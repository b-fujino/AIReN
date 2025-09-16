
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
from AIEngineCore import InterviewerEngine
from synthesizer_voice import synthesize_voice

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




# 聞き取りスタート
@app.route("/start_listening", methods=["POST"])
def start_Interview():
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return jsonify({"error": "Session ID is not provided"}), 400

    clients[session_id] = {"last_access": time.time()}
    # インタビュワーのインスタンス作成
    Interviewer = InterviewerEngine()
    clients[session_id]["Interviewer"] = Interviewer

    # ここに聞き取り開始の処理を実装
    FQ=clients[session_id]["Interviewer"].first_question()

    # # メッセージを返す
    # if not FQ:
    #     # socketio.emit('ai_response', {"session_id":session_id,'ai_response': FQ})
    #     return jsonify({"error": "Failed to get AI response"}), 400
    
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

    if session_id not in clients:  # もしまだセッションIDのクライアントが作られてなければ
        return jsonify({"error": "Session ID is not found. Please start listening first."}), 400

    Interviewer = clients[session_id]["Interviewer"]

    """
    2 ユーザからの入力（音声ファイル or テキスト）を受け取り
    """    
    # 音声ファイルが送信されてた場合
    if "file" in request.files:
        audio_file = request.files["file"]
        audio_path = os.path.join("uploads", f"input.wav") #Uploadされたファイルを残すならこっちをOn
        audio_file.save(audio_path)

        # 音声認識
        text = recognize_speech(audio_path, request.form["languageCode"])
        os.remove(audio_path) #Uploadされたファイルを削除

        # 音声認識の結果をWebSocketを通じてクライアントに通知
        if text:
            socketio.emit("SpeechRecognition",{"session_id":session_id,"text": text})
        else:
            return jsonify({"error": "Failed to recognize speech"}), 400  
          
    # テキストが送信されてきてた場合
    elif "text" in request.form:
        text = request.form["text"]

    # どちらでもない場合
    else:
        return jsonify({"error": "No audio file or text provided"}), 400


    """
    3 入力させたユーザのテキストをInterviewerに渡し，質問を生成させる
    """
    ai_response, has_next = Interviewer.run(text)

    """ 
    4.2 WebSocketを通じてクライアントに通知する
    """
    if ai_response:
        socketio.emit('ai_response', {"session_id":session_id,'ai_response': ai_response}) 
        # chatlog.append({"role":"assistant", "content": ai_response})
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
        final_summary = Interviewer.generate_final_summary()
        socketio.emit('summary', {"session_id":session_id,'summary': final_summary})
        
    return jsonify({"info": "Upload Process Succeeded"}), 200



# streaming処理するエンドポイント
@app.route("/streaming", methods=["POST"])
def chat_streaming():
    """
    1 タブごとにAIのオブジェクトを切り替えるための処理
    タブごとにセッションIDを送信させて，そのセッションIDに対応するクライアントを作成する
    """
    """
    1 タブごとにAIのオブジェクトを切り替えるための処理
    タブごとにセッションIDを送信させて，そのセッションIDに対応するクライアントを作成する
    """
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return jsonify({"error": "Session ID is not provided"}), 400

    if session_id not in clients:  # もしまだセッションIDのクライアントが作られてなければ
        return jsonify({"error": "Session ID is not found. Please start listening first."}), 400

    Interviewer = clients[session_id]["Interviewer"]

    """
    2 ユーザからの入力（音声ファイル or テキスト）を受け取り
    """    
    # 音声ファイルが送信されてた場合
    if "file" in request.files:
        audio_file = request.files["file"]
        audio_path = os.path.join("uploads", f"input.wav") #Uploadされたファイルを残すならこっちをOn
        audio_file.save(audio_path)

        # 音声認識
        text = recognize_speech(audio_path, request.form["languageCode"])
        os.remove(audio_path) #Uploadされたファイルを削除

        # 音声認識の結果をWebSocketを通じてクライアントに通知
        if text:
            socketio.emit("SpeechRecognition",{"session_id":session_id,"text": text})
        else:
            return jsonify({"error": "Failed to recognize speech"}), 400  
          
    # テキストが送信されてきてた場合
    elif "text" in request.form:
        text = request.form["text"]

    # どちらでもない場合
    else:
        return jsonify({"error": "No audio file or text provided"}), 400
    

    """
    3 入力させたユーザのテキストをInterviewerに渡し，質問を生成させる
    """

    """
    # AIの応答をストリームでフロントエンドに送信
    """
    sentences = "" # AIの応答を格納する文字列
    Duration = 0  # 総再生時間
    starttime = time.time() # 処理開始時間

    if request.form["OutputMode"] == "Voice": # 出力モードが音声の場合

        ai_response = Interviewer.run(text, Stream=True) #AIの節単位の応答を句単位でストリームする

        # AIの応答を句単位でストリームするとともに．句単位で音声合成もしていく
        socketio.emit('ai_stream', {"session_id":session_id,'sentens': "---Start---"}) # 開始を通知
        for sentence in ai_response:
        ## WebSocketを通じてクライアントに通知
            if sentence:
                sentences += sentence # AIの応答を追加
                #　音声合成（mp3出力）
                if not sentence or sentence.strip() == "": # sentence.strip()は、両端の空白・改行・タブなどを除去．その結果空文字ならcontinue
                    continue
                mp3_data, duration = synthesize_voice(sentence, request.form)
                # 総再生時間の取得
                Duration += duration
                if mp3_data is None: return jsonify({"error": "Failed to synthesize voice"}), 400
                ## mp3データをWebSocketを通じてクライアントに通知 ここでうまくキューに入れて連続再生させたい
                socketio.emit('ai_stream', {"session_id":session_id,'audio': mp3_data.getvalue(), 'sentens': sentence})
                
                # 実際には読点での句切り処理は辞めたので，以下のif文はほぼ意味ないが・・・
                #
                # sentensの区切り文字が読点だったら，0.2秒の無音を入れる
                if sentence[-1] in ",，、":
                    silent_audio = AudioSegment.silent(duration=10)
                    mp3_data  = BytesIO()
                    silent_audio.export(mp3_data , format="mp3")
                    mp3_data .seek(0)
                # sentensの区切り文字が読点でなかったら，0.5秒の無音を入れる
                else:
                    silent_audio = AudioSegment.silent(duration=500)
                    mp3_data  = BytesIO()
                    silent_audio.export(mp3_data , format="mp3")
                    mp3_data .seek(0)
                # 無音を送信
                socketio.emit('ai_stream', {"session_id":session_id,'audio': mp3_data.getvalue(), 'sentens': "---silent---"})
            else:
                return jsonify({"error": "Failed to get AI response"}), 400
        socketio.emit('ai_stream', {"session_id":session_id,'sentens': "---End---"}) # 終了を通知
        # 経過時間の確認．もし処理スタートからの経過時間が総再生時間より短ければ，その差分だけ待つ
        # これをやらないと，再生が終わる前に次の処理に進んでしまう．  
        elapsed_time = time.time() - starttime
        if elapsed_time < Duration:
            time.sleep(Duration - elapsed_time)

    else: # 出力モードがテキストの場合
        ai_response = Interviewer.run(text, Stream=True) #AIの節単位の応答を句単位でストリームする
        
        socketio.emit('ai_textstream', {"session_id":session_id,'sentens': "---Start---"}) # 開始を通知
        for sentence in ai_response: # 出力モードがテキストの場合
            sentences += sentence # AIの応答を追加
            if sentence is None: # OpenAIの応答だと空文字が返ることがある
                continue            
            if sentence =="": # 空文字の場合は何もしない
                continue
            socketio.emit('ai_textstream', {"session_id":session_id,'sentens': sentence})
            if sentence[-1] in SegmentingChars:
                time.sleep(0.5) # つぎの出力まで1秒待つ
            else:
                time.sleep(0.1) # つぎの出力まで0.5秒待つ
        socketio.emit('ai_textstream', {"session_id":session_id,'sentens': "---End---"}) # 終了を通知

    return jsonify({"info": "Process Succeeded"}), 200


# ログアウト処理を行うエンドポイント
@app.route('/logout', methods=['POST'])
def logout():
    """ブラウザが閉じられたらセッションを削除"""
    session_id = request.headers.get("X-Session-ID")
    if session_id and session_id in clients:
        del clients[session_id]
        print(f"Session {session_id} deleted")
    return jsonify({"message": "Session deleted"})


# Demo用のエンドポイント
stop_flag = False
@app.route("/demo", methods=["POST"])
def demo():
    # セッションIDの取得
    data = request.get_json(silent=True) or request.form.to_dict(flat=True)
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return jsonify({"error": "Session ID is not provided"}), 400

    if session_id not in clients:
        clients[session_id] = {"last_access": time.time()}
        clients[session_id]["Interviewer"] = InterviewerEngine()
    
    socketio.start_background_task(DemoInterview, session_id, data)  # ここでバックグラウンド開始
    return jsonify({"ok": True})   

def DemoInterview(session_id, data):
    global stop_flag
    stop_flag = False

    Interviewer = clients[session_id]["Interviewer"]

    Question = Interviewer.first_question(Stream=True)  # 最初の質問を生成

    # Questionを句単位でストリームする
    #region
    # AIの応答を句単位でストリームするとともに．句単位で音声合成もしていく
    socketio.emit('ai_stream', {"session_id":session_id,'sentens': "---Start---"}) # 開始を通知
    sentences = "" # AIの応答を格納する文字列
    Duration = 0  # 総再生時間
    starttime = time.time() # 処理開始時間
    for sentence in Question:
    ## WebSocketを通じてクライアントに通知
        if sentence:
            sentences += sentence # AIの応答を追加
            #　音声合成（mp3出力）
            if not sentence or sentence.strip() == "": # sentence.strip()は、両端の空白・改行・タブなどを除去．その結果空文字ならcontinue
                continue
            mp3_data, duration = synthesize_voice(sentence, data)
            # 総再生時間の取得
            Duration += duration
            if mp3_data is None: return jsonify({"error": "Failed to synthesize voice"}), 400
            ## mp3データをWebSocketを通じてクライアントに通知 ここでうまくキューに入れて連続再生させたい
            socketio.emit('ai_stream', {"session_id":session_id,'audio': mp3_data.getvalue(), 'sentens': sentence})
            
            # 実際には読点での句切り処理は辞めたので，以下のif文はほぼ意味ないが・・・
            #
            # sentensの区切り文字が読点だったら，0.2秒の無音を入れる
            if sentence[-1] in ",，、":
                silent_audio = AudioSegment.silent(duration=10)
                mp3_data  = BytesIO()
                silent_audio.export(mp3_data , format="mp3")
                mp3_data .seek(0)
            # sentensの区切り文字が読点でなかったら，0.5秒の無音を入れる
            else:
                silent_audio = AudioSegment.silent(duration=500)
                mp3_data  = BytesIO()
                silent_audio.export(mp3_data , format="mp3")
                mp3_data .seek(0)
            # 無音を送信
            socketio.emit('ai_stream', {"session_id":session_id,'audio': mp3_data.getvalue(), 'sentens': "---silent---"})
        else:
            return jsonify({"error": "Failed to get AI response"}), 400
    done = threading.Event()
    def on_complete():
        done.set()
    socketio.emit('ai_stream', {"session_id":session_id,'sentens': "---End---"}, callback=on_complete) # 終了を受け取るまで待機
    done.wait()  # 終了を待機

    Question = sentences
    print("Interviewer:", Question)
    #endregion

    has_next = True
    while has_next:
        if stop_flag:
            break

        """Reporterからの応答を取得"""
        #region
        report = Interviewer.generate_report(Question, Stream=False) # Reporterの応答をストリームしない
        if report:
            socketio.emit('demo', {"session_id":session_id,'user': report})
        else:
            return jsonify({"error": "Failed to get AI response"}), 400
        
        if stop_flag:
            break
        
        # 音声作り VoiceVoxに与える
        form =data.copy()
        form["TTS"] = "VoiceVox"
        form["speakerId"] = 11
        # form["speed"] = request.form["speed"]
        # form["pitch"] = request.form["pitch"]
        # form["intonation"] = request.form["intonation"]

        if data["OutputMode"] == "Voice":
            mp3_data,duration = synthesize_voice(report, form) 
            done = threading.Event()
            def on_complete():
                print("Report:", report)
                done.set()
            socketio.emit('play_audio', {"session_id":session_id,'audio': mp3_data.getvalue(),'demo':'report'}, callback=on_complete)
            done.wait()  # 終了を待機

        #endregion

        if stop_flag:
            break

        """Interviewerの次の質問を生成"""
        Question, has_next = Interviewer.run(report, Stream=True) #AIの節単位の応答を句単位でストリームする
        #region
        # AIの応答を句単位でストリームするとともに．句単位で音声合成もしていく
        socketio.emit('ai_stream', {"session_id":session_id,'sentens': "---Start---"}) # 開始を通知
        sentences = "" # AIの応答を格納する文字列
        Duration = 0  # 総再生時間
        for sentence in Question:
        ## WebSocketを通じてクライアントに通知
            if sentence:
                sentences += sentence # AIの応答を追加
                #　音声合成（mp3出力）
                if not sentence or sentence.strip() == "": # sentence.strip()は、両端の空白・改行・タブなどを除去．その結果空文字ならcontinue
                    continue                
                mp3_data, duration = synthesize_voice(sentence, data)
                # 総再生時間の取得
                Duration += duration
                if mp3_data is None: return jsonify({"error": "Failed to synthesize voice"}), 400
                ## mp3データをWebSocketを通じてクライアントに通知 ここでうまくキューに入れて連続再生させたい
                socketio.emit('ai_stream', {"session_id":session_id,'audio': mp3_data.getvalue(), 'sentens': sentence})
                
                # 実際には読点での句切り処理は辞めたので，以下のif文はほぼ意味ないが・・・
                #
                # sentensの区切り文字が読点だったら，0.2秒の無音を入れる
                if sentence[-1] in ",，、":
                    silent_audio = AudioSegment.silent(duration=10)
                    mp3_data  = BytesIO()
                    silent_audio.export(mp3_data , format="mp3")
                    mp3_data .seek(0)
                # sentensの区切り文字が読点でなかったら，0.5秒の無音を入れる
                else:
                    silent_audio = AudioSegment.silent(duration=500)
                    mp3_data  = BytesIO()
                    silent_audio.export(mp3_data , format="mp3")
                    mp3_data .seek(0)
                # 無音を送信
                socketio.emit('ai_stream', {"session_id":session_id,'audio': mp3_data.getvalue(), 'sentens': "---silent---"})
            else:
                return jsonify({"error": "Failed to get AI response"}), 400
        done = threading.Event()
        def on_complete():
            done.set()
        socketio.emit('ai_stream', {"session_id":session_id,'sentens': "---End---"}, callback=on_complete) # 終了を受け取るまで待機
        done.wait()  # 終了を待機
        Question = sentences
        print("Interviewer:", Question)   
        #endregion 

        if stop_flag:
            break
    
    # これまでのインタビューを要約して，クライアントに通知する
    final_summary = Interviewer.generate_final_summary()
    final_summary_md = Interviewer.json_to_md(final_summary) # JSONをMarkdownに変換
    socketio.emit('summary', {"session_id":session_id,'summary': final_summary_md})



    return jsonify({"info": "Demo Process Succeeded"}), 200



# Demoの停止処理を行うエンドポイント
@app.route("/demo_stop", methods=["POST"])
def demo_stop():
    global stop_flag
    stop_flag = True
    return jsonify({"info": "Demo Stop Process Succeeded"}), 200


#  古いセッションを削除する関数 現時点では1時間00～10分で削除
def cleanup_old_clients(timeout=3600):
    while True:
        now = time.time()
        expired_sessions = [s_id for s_id, data in clients.items() if now - data["last_access"] > timeout]
        for s_id in expired_sessions:
            del clients[s_id]  # 古いクライアントを削除
            print(f"Deleted expired session: {s_id}")
        time.sleep(60*10)  # 10分ごとにチェック

#  バックグラウンドでクリーンアップ処理を実行
cleanup_thread = threading.Thread(target=cleanup_old_clients, daemon=True)
cleanup_thread.start()

#  
#--------------------------------------------------
    
if __name__ == "__main__":
    logging.info("#####アプリケーションを起動します。#####")
    socketio.run(app, debug=True, port = 5000)
