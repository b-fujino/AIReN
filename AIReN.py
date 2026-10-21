
"""
# インタビューエージェントのバックエンドプログラム

## 履歴
- 2025/03/18: Sessionに対応 Sessionは約60分で切れる．
- 2025/05/03: 画像を表示
- 2025/06/03: pythonライブラリアップデート
− 2025/06/04: 画像にかかわるバグ（大文字小文字の区別）を修正

- 2025/08/25: AIエンジンとの統合
-------------------
## 未対応案件
- ストリーミング対応
- Google TTSのBillingの設定
"""
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import speech_recognition as sr
from dotenv import load_dotenv
import requests
import time
import logging
import json
from pydub import AudioSegment
from io import BytesIO
import base64
import threading
import uuid
from AIEngineCore import InterviewerEngine, json_to_md
from synthesizer_voice import synthesize_voice
from pyngrok import ngrok


#　環境変数の読み込み
load_dotenv()



# Flaskアプリケーションの作成
app = Flask(__name__, static_folder="static")  

# セッションの設定
app.secret_key = os.getenv("FLASK_SECRET_KEY")
clients = {}  # セッションIDごとのクライアント情報を保存する辞書


# CORSの設定
CORS(app)

# Socket.IOの設定
socketio = SocketIO(app,  cors_allowed_origins="*")

# 区切り文字の設定．AI出力をストリームで受け取るときに句切りをどの文字で行なうかの指定
# この文字が来たら，その前までを一つの句として扱う
SegmentingChars="。．.:;？?！!\n" # + ",，、"

#loggingの設定
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="app.log",
    encoding="utf-8"
)




#--------------------------------------------------
# 各種処理の関数
#--------------------------------------------------

def recognize_speech(audio_path, languageCode):
    """
    # 音声認識を行う関数

    args:
    ------------------------
    audio_path: 
        音声ファイルのパス
    languageCode: 
        言語コード

    return:
    ------------------------
    text: 
        認識結果のテキスト
    """
    r = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = r.record(source)
        text = r.recognize_google(audio, language=languageCode)
    return text



#--------------------------------------------------
# Flaskのエンドポイントの作成
#--------------------------------------------------



# ルートパスへのリクエストを処理する
@app.route("/")
def index():
    return send_from_directory("static", "index.html")



# VoiceVoxのSpeakerIDリストを取得するエンドポイント
@app.route("/speaker_ids")
def get_speaker_ids():
    VOICEVOX_API_URL = "http://localhost:50021"
    url = f"{VOICEVOX_API_URL}/speakers"  # VOICEVOX APIのエンドポイント
    try:
        response = requests.get(url)
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"error": f"Error: {e}"}), 500
    
    voicevox_speakers = []
    if response.status_code == 200:
        speakers = response.json()
        for speaker in speakers:
            name = speaker['name']
            style_names = [style['name'] for style in speaker['styles']]
            style_ids = [style['id'] for style in speaker['styles']]
            for style_id, style_name in zip(style_ids, style_names):
                voicevox_speakers.append(f"<option value={style_id}>{name}, {style_name} </option>")
        logging.info("speaker_ids を取得しました。")
        return jsonify(voicevox_speakers)
    else:
        logging.error(f"Error: {response.status_code}")
        return jsonify({"error": "Failed to fetch speaker IDs"}), response.status_code




# 音声テストを行うエンドポイント
@app.route("/speaker_test" , methods=["POST"])
def speaker_test():
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return jsonify({"error": "Session ID is not provided"}), 400
    TTS = request.form["TTS"]
    speaker = request.form["speakerId"]
    languageCode = request.form["languageCode"]

    logging.debug(f"speaker_test: TTS={TTS}, speaker={speaker}, languageCode={languageCode} ") #, JPvoicetype={JPvoicetype}, ENvoicetype={ENvoicetype}

    if TTS == "VoiceVox":
        text = "こんにちは．初めまして．何かお手伝いできることはありますか？"
    elif TTS == "GPTSoVITS":
        text = "こんにちはだっちゃ。初めましてだっちゃ。何か手伝ってほしいことがあるのけ？"

    else:
        return jsonify({"error": "Failed to synthesize voice_Test. Input TTS is irregal"}), 400

    # 音声合成
    mp3_data, duration = synthesize_voice(text, request.form)
    if mp3_data is None: return jsonify({"error": "Failed to synthesize voice"}), 400
    socketio.emit('play_audio', {"session_id":session_id,'audio': mp3_data.getvalue()})
    return jsonify({"info": "Speaker Test Process Succeeded"}), 200




#--------------------------------------------------
# セッション・入出力の共通処理
#--------------------------------------------------

def get_client(session_id):
    """セッションIDに対応するクライアント情報を返し，最終アクセス時刻を更新する．なければNone．
    """
    client = clients.get(session_id)
    if client is not None:
        client["last_access"] = time.time()
    return client


def get_user_text(session_id):
    """リクエストからユーザの入力（音声ファイル or テキスト）を取り出してテキストで返す．
    失敗したら(None, エラーレスポンス)を返す．
    """
    # 音声ファイルが送信されてた場合
    if "file" in request.files:
        audio_file = request.files["file"]
        os.makedirs("uploads", exist_ok=True)
        audio_path = os.path.join("uploads", f"input_{uuid.uuid4().hex}.wav") # 同時アクセスで上書きしないように一意な名前にする
        audio_file.save(audio_path)
        try:
            # 音声認識
            text = recognize_speech(audio_path, request.form["languageCode"])
        except (sr.UnknownValueError, sr.RequestError) as e:
            logging.error(f"Speech recognition failed: {e}")
            text = None
        finally:
            os.remove(audio_path) #Uploadされたファイルを削除

        # 音声認識の結果をWebSocketを通じてクライアントに通知
        if text:
            socketio.emit("SpeechRecognition",{"session_id":session_id,"text": text})
            return text, None
        return None, (jsonify({"error": "Failed to recognize speech"}), 400)

    # テキストが送信されてきてた場合
    if "text" in request.form:
        return request.form["text"], None

    # どちらでもない場合
    return None, (jsonify({"error": "No audio file or text provided"}), 400)


def make_silence(duration_ms):
    """無音のmp3データを作成する"""
    silent_audio = AudioSegment.silent(duration=duration_ms)
    mp3_data = BytesIO()
    silent_audio.export(mp3_data, format="mp3")
    mp3_data.seek(0)
    return mp3_data


def wait_client_ack(event, data, timeout=300):
    """クライアントがコールバックを返すまで待機する（切断時に永久に待たないようタイムアウト付き）"""
    done = threading.Event()
    def on_complete(*args):
        done.set()
    socketio.emit(event, data, callback=on_complete)
    if not done.wait(timeout):
        logging.warning(f"Timeout waiting for client ack: {event}")


def emit_voice_stream(session_id, sentence_iter, form, wait_end=False):
    """AIの応答を句単位で音声合成しながら'ai_stream'でクライアントに送信する．
    ---
    returns:
        (全文, 総再生時間)．音声合成に失敗したら(None, 総再生時間)
    """
    sentences = "" # AIの応答を格納する文字列
    Duration = 0  # 総再生時間
    socketio.emit('ai_stream', {"session_id":session_id,'sentens': "---Start---"}) # 開始を通知
    for sentence in sentence_iter:
        if not sentence:
            continue
        sentences += sentence # AIの応答を追加
        if sentence.strip() == "": # 両端の空白・改行・タブなどを除去した結果が空文字なら音声合成しない
            continue
        #　音声合成（mp3出力）
        mp3_data, duration = synthesize_voice(sentence, form)
        if mp3_data is None:
            socketio.emit('ai_stream', {"session_id":session_id,'sentens': "---End---"})
            return None, Duration
        Duration += duration # 総再生時間の取得
        ## mp3データをWebSocketを通じてクライアントに通知
        socketio.emit('ai_stream', {"session_id":session_id,'audio': mp3_data.getvalue(), 'sentens': sentence})

        # 句の区切りが読点なら短い無音，そうでなければ0.5秒の無音を入れる
        mp3_data = make_silence(10 if sentence[-1] in ",，、" else 500)
        socketio.emit('ai_stream', {"session_id":session_id,'audio': mp3_data.getvalue(), 'sentens': "---silent---"})

    end_msg = {"session_id":session_id,'sentens': "---End---"}
    if wait_end:
        wait_client_ack('ai_stream', end_msg) # 終了を受け取るまで待機
    else:
        socketio.emit('ai_stream', end_msg) # 終了を通知
    return sentences, Duration


def emit_final_summary(session_id, Interviewer):
    """これまでのインタビューを要約して，Markdownでクライアントに通知する"""
    final_summary = Interviewer.generate_final_summary()
    socketio.emit('summary', {"session_id":session_id,'summary': json_to_md(final_summary)})



#--------------------------------------------------
# 聞き取りのエンドポイント
#--------------------------------------------------

# 聞き取りスタート
@app.route("/start_listening", methods=["POST"])
def start_Interview():
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return jsonify({"error": "Session ID is not provided"}), 400

    # インタビュワーのインスタンス作成
    clients[session_id] = {"last_access": time.time(), "Interviewer": InterviewerEngine(), "stop": False}

    # ここに聞き取り開始の処理を実装
    FQ=clients[session_id]["Interviewer"].first_question()

    #音声モードなら音声合成して返す
    if request.form["OutputMode"] == "Voice":
        # AIの応答から音声合成してmp3で返す
        mp3_data, duration = synthesize_voice(FQ, request.form)
        if mp3_data is None: return jsonify({"error": "Failed to synthesize voice"}), 400

        # mp3データをWebSocketを通じてクライアントに通知
        socketio.emit('play_audio', {"session_id":session_id,'audio': mp3_data.getvalue()})

    # メッセージを返す
    return jsonify({"info": "Listening started", "message": FQ}), 200



# /upload へのリクエストを処理する
@app.route("/upload", methods=["POST"])
def chat():
    """
    1 タブごとにAIのオブジェクトを切り替えるための処理
    タブごとにセッションIDを送信させて，そのセッションIDに対応するクライアントを作成する
    """
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return jsonify({"error": "Session ID is not provided"}), 400

    client = get_client(session_id)
    if client is None:  # もしまだセッションIDのクライアントが作られてなければ
        return jsonify({"error": "Session ID is not found. Please start listening first."}), 400

    Interviewer = client["Interviewer"]
    if Interviewer.finished:
        return jsonify({"error": "Interview has already finished."}), 400

    """
    2 ユーザからの入力（音声ファイル or テキスト）を受け取り
    """
    text, error = get_user_text(session_id)
    if error: return error


    """
    3 入力させたユーザのテキストを報告としてInterviewerに渡し，質問を生成させる
    """
    ai_response, has_next = Interviewer.run(Report=text)

    """
    4.2 WebSocketを通じてクライアントに通知する
    """
    if ai_response:
        socketio.emit('ai_response', {"session_id":session_id,'ai_response': ai_response})
    else:
        return jsonify({"error": "Failed to get AI response"}), 400

    """
    4.3 出力モードが音声の場合，音声を生成してWebSocketを通じてクライアントに通知
    """
    if request.form["OutputMode"] == "Voice":
        # AIの応答から音声合成してmp3で返す
        mp3_data, duration = synthesize_voice(ai_response, request.form)
        if mp3_data is None: return jsonify({"error": "Failed to synthesize voice"}), 400

        # mp3データをWebSocketを通じてクライアントに通知
        socketio.emit('play_audio', {"session_id":session_id,'audio': mp3_data.getvalue()})

    if has_next == False:
        # これまでのインタビューを要約して，クライアントに通知する
        emit_final_summary(session_id, Interviewer)

    return jsonify({"info": "Upload Process Succeeded"}), 200



# streaming処理するエンドポイント
@app.route("/streaming", methods=["POST"])
def chat_streaming():
    """
    1 タブごとにAIのオブジェクトを切り替えるための処理
    タブごとにセッションIDを送信させて，そのセッションIDに対応するクライアントを作成する
    """
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return jsonify({"error": "Session ID is not provided"}), 400

    client = get_client(session_id)
    if client is None:  # もしまだセッションIDのクライアントが作られてなければ
        return jsonify({"error": "Session ID is not found. Please start listening first."}), 400

    Interviewer = client["Interviewer"]
    if Interviewer.finished:
        return jsonify({"error": "Interview has already finished."}), 400

    """
    2 ユーザからの入力（音声ファイル or テキスト）を受け取り
    """
    text, error = get_user_text(session_id)
    if error: return error


    """
    3 入力させたユーザのテキストを報告としてInterviewerに渡し，質問を句単位のストリームで受け取る
    """
    ai_response, has_next = Interviewer.run(Report=text, Stream=True)

    """
    # AIの応答をストリームでフロントエンドに送信
    """
    if request.form["OutputMode"] == "Voice": # 出力モードが音声の場合
        starttime = time.time() # 処理開始時間
        # AIの応答を句単位でストリームするとともに．句単位で音声合成もしていく
        sentences, Duration = emit_voice_stream(session_id, ai_response, request.form)
        if sentences is None: return jsonify({"error": "Failed to synthesize voice"}), 400
        # 経過時間の確認．もし処理スタートからの経過時間が総再生時間より短ければ，その差分だけ待つ
        # これをやらないと，再生が終わる前に次の処理に進んでしまう．
        elapsed_time = time.time() - starttime
        if elapsed_time < Duration:
            time.sleep(Duration - elapsed_time)

    else: # 出力モードがテキストの場合
        socketio.emit('ai_textstream', {"session_id":session_id,'sentens': "---Start---"}) # 開始を通知
        for sentence in ai_response:
            if not sentence: # OpenAIの応答だとNoneや空文字が返ることがある
                continue
            socketio.emit('ai_textstream', {"session_id":session_id,'sentens': sentence})
            if sentence[-1] in SegmentingChars:
                time.sleep(0.5) # 句の区切りなら0.5秒待つ
            else:
                time.sleep(0.1) # そうでなければ0.1秒待つ
        socketio.emit('ai_textstream', {"session_id":session_id,'sentens': "---End---"}) # 終了を通知

    if has_next == False:
        # これまでのインタビューを要約して，クライアントに通知する
        emit_final_summary(session_id, Interviewer)

    return jsonify({"info": "Process Succeeded"}), 200


# ログアウト処理を行うエンドポイント
@app.route('/logout', methods=['POST'])
def logout():
    """ブラウザが閉じられたらセッションを削除"""
    session_id = request.headers.get("X-Session-ID")
    if session_id and session_id in clients:
        clients.pop(session_id, None)
        print(f"Session {session_id} deleted")
    return jsonify({"message": "Session deleted"})


# Demo用のエンドポイント
@app.route("/demo", methods=["POST"])
def demo():
    # セッションIDの取得
    data = request.get_json(silent=True) or request.form.to_dict(flat=True)
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return jsonify({"error": "Session ID is not provided"}), 400

    # デモは常に新しいインタビューとして開始する
    clients[session_id] = {"last_access": time.time(), "Interviewer": InterviewerEngine(), "stop": False}

    socketio.start_background_task(DemoInterview, session_id, data)  # ここでバックグラウンド開始
    return jsonify({"ok": True})


def DemoInterview(session_id, data):
    """デモ用にAIReporterを相手にしたインタビューをバックグラウンドで実行する．
    リクエストコンテキスト外で動くので，エラー時はログに残して終了する（jsonifyは使えない）．
    """
    client = clients.get(session_id)
    if client is None:
        return
    Interviewer = client["Interviewer"]

    def stopped():
        # セッションが削除された場合も停止扱いにする
        c = clients.get(session_id)
        return c is None or c.get("stop", False)

    Question = Interviewer.first_question(Stream=True)  # 最初の質問を生成

    # Questionを句単位でストリームする
    Question, _ = emit_voice_stream(session_id, Question, data, wait_end=True)
    if Question is None:
        logging.error("Demo: Failed to synthesize voice")
        return
    print("Interviewer:", Question)

    has_next = True
    while has_next:
        if stopped():
            break

        """Reporterからの応答を取得"""
        #region
        report = Interviewer.generate_report(Question, Stream=False) # Reporterの応答をストリームしない
        if not report:
            logging.error("Demo: Failed to get AI reporter response")
            return
        socketio.emit('demo', {"session_id":session_id,'user': report})

        if stopped():
            break

        # 音声作り VoiceVoxに与える
        form =data.copy()
        form["TTS"] = "VoiceVox"
        form["speakerId"] = 11

        if data["OutputMode"] == "Voice":
            mp3_data,duration = synthesize_voice(report, form)
            if mp3_data is None:
                logging.error("Demo: Failed to synthesize voice")
                return
            wait_client_ack('play_audio', {"session_id":session_id,'audio': mp3_data.getvalue(),'demo':'report'}) # 再生終了を待機
            print("Report:", report)
        #endregion

        if stopped():
            break

        """Interviewerの次の質問を生成"""
        Question, has_next = Interviewer.run(Report=report, Stream=True) #AIの節単位の応答を句単位でストリームする
        Question, _ = emit_voice_stream(session_id, Question, data, wait_end=True)
        if Question is None:
            logging.error("Demo: Failed to synthesize voice")
            return
        print("Interviewer:", Question)

    if session_id not in clients:
        return
    # これまでのインタビューを要約して，クライアントに通知する
    emit_final_summary(session_id, Interviewer)



# Demoの停止処理を行うエンドポイント
@app.route("/demo_stop", methods=["POST"])
def demo_stop():
    session_id = request.headers.get("X-Session-ID")
    client = clients.get(session_id) if session_id else None
    if client is None:
        return jsonify({"error": "Session ID is not found."}), 400
    client["stop"] = True # このセッションのデモだけを停止する
    return jsonify({"info": "Demo Stop Process Succeeded"}), 200


#  古いセッションを削除する関数 現時点では最終アクセスから1時間00～10分で削除
def cleanup_old_clients(timeout=3600):
    while True:
        now = time.time()
        expired_sessions = [s_id for s_id, data in list(clients.items()) if now - data["last_access"] > timeout]
        for s_id in expired_sessions:
            clients.pop(s_id, None)  # 古いクライアントを削除
            print(f"Deleted expired session: {s_id}")
        time.sleep(60*10)  # 10分ごとにチェック

#  バックグラウンドでクリーンアップ処理を実行
cleanup_thread = threading.Thread(target=cleanup_old_clients, daemon=True)
cleanup_thread.start()

#
#--------------------------------------------------

if __name__ == "__main__":
    logging.info("#####アプリケーションを起動します。#####")

    # ngrokで外部公開するため，デバッグモード（Werkzeugデバッガ）は環境変数で明示したときだけ有効にする
    debug = os.getenv("FLASK_DEBUG", "0") == "1"

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        ngrok.set_auth_token(os.getenv("NGROK_AUTH_TOKEN"))
        ngrok.kill()
        public_url = ngrok.connect(addr="127.0.0.1:5000")
        print("ngrokトンネル公開URL:", public_url)


    # Flask-SocketIOはdebug=FalseだとWerkzeugサーバーでの起動を拒否するため，明示的に許可する（デバッガは無効のまま）
    socketio.run(app, debug=debug, port = 5000, allow_unsafe_werkzeug=True)
