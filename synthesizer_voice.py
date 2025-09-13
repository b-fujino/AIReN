from pydub import AudioSegment
from io import BytesIO
import logging
import requests
from gradio_client import Client
import soundfile as sf


#loggingの設定
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="app.log",
    encoding="utf-8"
)

# VoiceVox APIのエンドポイント
VOICEVOX_API_URL = "http://localhost:50021"

def synthesize_voice(text, form):
    """
    各種APIを使って音声合成を行うラッパー関数

    args:
    ------------------------
    text: 
        音声合成するテキスト
    form: 
        リクエストフォーム
        フォームの内容は以下の通り
            TTS: 音声合成の種類（VoiceVox or Google）
            speakerId: VoiceVoxのSpeakerID
            languageCode: 言語コード
            JPvoicetype: 日本語の音声タイプ
            ENvoicetype: 英語の音声タイプ
            speed: 速度
            pitch: ピッチ
            intonation: 抑揚

    return:
    ------------------------
    mp3_data: 
        音声合成された音声データ
    duration: 
        再生時間（秒）
    """
    # TTSの種類情報を取得
    TTS = form["TTS"]
    if TTS == "VoiceVox":
        speaker = form["speakerId"]
    else:
        speaker = None
    languageCode = form["languageCode"]
    # JPvoicetype = form["JPvoicetype"]
    # ENvoicetype = form["ENvoicetype"]
    speed = float(form["speed"])
    pitch = float(form["pitch"] )
    intonation = float(form["intonation"])

    logging.debug(f"speaker_test: TTS={TTS}, speaker={speaker}, languageCode={languageCode}") #, JPvoicetype={JPvoicetype}, ENvoicetype={ENvoicetype}

    #Textに読み上げしない文字が含まれてる場合はその文字をTextから外す
    text = text.replace("#", "") # 見出し文字#を削除
    text = text.replace("*", "") # 協調表示や見出し記号の*を削除

    if TTS == "VoiceVox":
        mp3_data = synthesize_voicevox_mp3(text, speaker, speed, pitch, intonation)
    # elif TTS == "Google":
    #     # 日本語と英語で分岐
    #     if languageCode == "ja-JP":
    #         voicetype = JPvoicetype
    #     elif languageCode == "en-US":
    #         voicetype = ENvoicetype
    #     else:# 日本語でも英語でもない場合
    #         return jsonify({"error": "Failed to synthesize voice_Test. Input languageCode is irregal"}), 400
    #     # Google Cloud TTS APIで音声合成
    #     mp3_data = synthesize_voice_google(text,languageCode, voicetype, speed, pitch)
    elif TTS == "GPTSoVITS":
        # Lumの音声合成を行う
        mp3_data = synthesize_voice_Lum(text)
        if mp3_data is None:
            logging.error("Error in synthesis: Lum synthesis failed")
            return None, 400
    else: # TTSがVoiceVoxでもGoogleでもない場合
        logging.error("Failed to synthesize voice_Test. Input TTS is irregal")
        return None, 400

    if mp3_data is None: 
        return None, 400

    # mp3 データを返す   
    audio = AudioSegment.from_file(mp3_data, format="mp3")
    duration = len(audio) / 1000.0  # ミリ秒を秒に変換     
    return mp3_data, duration

def synthesize_voicevox(text, speaker, speed, pitch, intonation):
    """
    # VoiceVox APIで音声合成を行う関数 (wav出力)

    args:
    ------------------------
    text: 音声合成するテキスト
    speaker: SpeakerID
    speed: 速度
    pitch: ピッチ
    intonation: 抑揚

    return:
    ------------------------
    synthesis_response: 音声合成された音声データ（wav）
    """    
    # 1. テキストから音声合成のためのクエリを作成
    query_payload = {
        'text': text, 
        'speaker': speaker, 
    }
    query_response = requests.post(f'{VOICEVOX_API_URL}/audio_query', params=query_payload)

    if query_response.status_code != 200:
        logging.error(f"Error in audio_query: {query_response.text}")
        return

    query = query_response.json()
    # 速度、ピッチ、抑揚を設定
    query["speedScale"] = speed
    query["pitchScale"] = pitch*0.15
    query["intonationScale"] = intonation

    # 2. クエリを元に音声データを生成
    synthesis_payload = {'speaker': speaker}

    # 音声データを生成
    synthesis_response = requests.post(f'{VOICEVOX_API_URL}/synthesis', params=synthesis_payload, json=query)
    if synthesis_response.status_code == 200:
        logging.info("音声データを生成しました。")
        return synthesis_response
    else:
        logging.error(f"Error in synthesis: {synthesis_response.text}")
        return None

def synthesize_voicevox_mp3(text, speaker, speed, pitch, intonation):
    """
    # voicevox で音声合成を行う関数（mp3出力）

    args:
    ------------------------
    text: 音声合成するテキスト
    speaker: SpeakerID
    speed: 速度
    pitch: ピッチ
    intonation: 抑揚

    return:
    ------------------------
    mp3_data: 音声合成された音声データ
    """
        # voicecvox apiでwavデータを生成
    synthesis_response = synthesize_voicevox(text, speaker, speed, pitch, intonation)

    if synthesis_response.status_code == 200:
        logging.info("音声データを生成しました。")
        audio = AudioSegment.from_file(BytesIO(synthesis_response.content), format="wav")
        mp3_data  = BytesIO()
        audio.export(mp3_data , format="mp3")
        mp3_data .seek(0)  
        return mp3_data
    else:
        logging.error(f"Error in synthesis: {synthesis_response.text}")
        return None

# def synthesize_voice_google(text,langcode, voicetype, speed, pitch):
#     """
#     # Google Clout TTS APIで音声合成を行う関数

#     args:
#     ------------------------
#     text: 音声合成するテキスト
#     langcode: 言語コード
#     voicetype: 音声タイプ
#     speed: 速度
#     pitch: ピッチ

#     return:
#     ------------------------
#     mp3_data: 音声合成された音声データ
#     """
#     # APIキーの取得
#     API_KEY = os.getenv("GOOGLE_TTS_API_KEY")

#     # APIエンドポイント
#     url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_KEY}"

#     # 音声合成のリクエストデータ
#     pitch = pitch*20
#     data = {
#         "input": {"text": text},
#         "voice": {
#             "languageCode": langcode,
#             "name": voicetype,  
# #            "ssmlGender": "MALE"
#         },
#         "audioConfig": {
#             "audioEncoding": "MP3",
#             "speakingRate": speed,
#             "pitch": pitch
#         }
#     }

#     # リクエスト送信
#     response = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(data))

#     # 結果を取得
#     if response.status_code == 200:
#         # Base64エンコードされた音声データをデコード
#         audio_content = json.loads(response.text)["audioContent"]
#         audio_data = base64.b64decode(audio_content)
        
#         # バイナリデータを pydub の AudioSegment に変換
#         mp3_data  =BytesIO(audio_data)
#         mp3_data .seek(0)  
#         return mp3_data
#     else:
#         logging.error(f"Error in synthesis: {response.text}")
#         return None





def synthesize_voice_Lum(text):
    """
    # Lumの音声合成を行う関数

    args:
    ------------------------
    text: 音声合成するテキスト

    return:
    ------------------------
    mp3_data: 音声合成された音声データ
    """
    # Gradio Clientの作成
    # ここではGradioのAPIを使って音声合成を行う
    # 事前にGradioのインターフェースをデプロイしておく必要があります。
    # 例: LumのGradioインターフェースのURLを指定
    client = Client("http://127.0.0.1:7860")
    result = client.predict(
            target_text=text,
            api_name="/predict"
    )
    print(result)  # ファイルパスを取得

    # 3. MP3変換
    audio = AudioSegment.from_file(result, format="wav")
    mp3_data = BytesIO()
    audio.export(mp3_data, format="mp3")
    mp3_data.seek(0)
    logging.info("Lumの音声合成を行いました。")
    return mp3_data
