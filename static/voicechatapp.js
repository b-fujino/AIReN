// Description: ボイスチャットアプリのフロントエンド処理を記述

//SessionIDの取得
let sessionId = sessionStorage.getItem("session_id");
if (!sessionId) {
    sessionId = crypto.randomUUID();  // ランダムなUUIDを生成
    sessionStorage.setItem("session_id", sessionId);
}


// 音声処理用の変数
let audioContext; // 音声処理用のコンテキスト
let recorder; // 録音用のオブジェクト
let audioBlob; // 録音した音声データ
let audioQueue = []; // 音声ファイルのキュー
let sentensQueue = []; // センテンスのキュー
let isPlaying = false; // 音声ファイル再生中かどうか
let currentDiv = ""; // 現在のdiv要素



// html要素取得
const h_radioTextInput = document.getElementById("radioTextInput");
const h_radioVoiceInput = document.getElementById("radioVoiceInput");
const h_radioTextOutput = document.getElementById("radioTextOutput");
const h_radioVoiceOutput = document.getElementById("radioVoiceOutput");
const h_btnGetFQ = document.getElementById("getFirtstQ");
const h_btnStartRec = document.getElementById("startRecording");
const h_btnStopRec = document.getElementById("stopRecording");
const h_btnSpeakerTest = document.getElementById("speakerTest");
const h_btnChatTextInput = document.getElementById("chatInputButton");
const h_selectSpeaker = document.getElementById("speakerSelect");
const h_chatlog = document.getElementById("chatlog");

const h_languageCode = document.querySelector(
  'input[name="languageCode"]:checked'
);
const h_radioVoicevoxTTS = document.getElementById("radioVoicevoxTTS");
const h_radioGPTSoVITS = document.getElementById("radioGPTSoVITS");
const h_TTS = document.querySelector('input[name="TTS"]:checked');
const h_spanSpeedValue = document.getElementById("spanSpeedValue");
const h_spanPitchValue = document.getElementById("spanPitchValue");
const h_spanIntonationValue = document.getElementById("spanIntonationValue");
const h_rangeSpeed = document.getElementById("rangeSpeed");
const h_rangePitch = document.getElementById("rangePitch");
const h_rangeIntonation = document.getElementById("rangeIntonation");
const h_chatTextInputArea=document.getElementById("chatInputText")



const h_img = document.getElementById("image1");
const h_img2 = document.getElementById("image2");
const h_img3 = document.getElementById("image3");


// 録音開始時のボタンを無効化
function setBtnonStart() {
  h_btnStartRec.disabled = true;
  h_btnStopRec.disabled = false;
  h_btnSpeakerTest.disabled = true;

  //要素の操作を全て無効化
  document.getElementById("Setting").style.pointerEvents = "none";
}

// 処理中のボタン無効化
function setBtnunderProcessing() {
  h_btnStartRec.disabled = true;
  h_btnStopRec.disabled = true;
  h_btnSpeakerTest.disabled = true;

  //要素の操作を全て無効化
  document.getElementById("Setting").style.pointerEvents = "none";
}

// 復帰時のボタン有効化
function setBtnonRestart() {
  h_btnStartRec.disabled = false;
  h_btnStopRec.disabled = true;
  h_btnSpeakerTest.disabled = false;
  //要素の操作を全て無効化
  document.getElementById("Setting").style.pointerEvents = "auto";
}

// formsの値を取得してJSON形式で返す
function getFormValues() {
  const data = new FormData(document.getElementById("myForm"));
  const obj = {};
  data.forEach((value, key) => {
    obj[key] = value;
  });
  console.log(obj);
  return obj;
}

// マイクのアクセス許可を取得
navigator.mediaDevices
  .getUserMedia({ audio: true })
  .then((stream) => {
    window.stream = stream;
  })
  .catch((error) => {
    console.error("Error accessing the microphone: " + error);
  });

// VoiceVoxの話者リストを取得
fetch("/speaker_ids")
  .then((response) => response.json())
  .then((data) => {
    h_selectSpeaker.innerHTML = data.join("");
    h_selectSpeaker.disabled = false;
    h_radioVoicevoxTTS.disabled = false;
  })
  .catch((error) => {
    console.error("Failed to get the list of speakers: " + error);
    h_radioVoicevoxTTS.disabled = true;
  });

/****** socket.ioの処理 *****/
// Socket.IO サーバーに接続
const socket = io();

// 音声認識の結果を受信
socket.on("SpeechRecognition", (data) => {
  if (data.session_id != sessionId)  return;
  const markdownText = data.text;
  const htmlContent = marked.parse(markdownText);
  h_chatlog.innerHTML += `<div class="user">${htmlContent}</div>`;
  h_chatlog.scrollTop = h_chatlog.scrollHeight;
});

//　Summaryの受信
socket.on("summary", (data) => {
  if (data.session_id != sessionId)  return;
  console.log(data.summary);
  const markdownText = data.summary;
  const htmlContent = marked.parse(markdownText);
  document.getElementById("summary").innerHTML = htmlContent;
});

//　Demo Userの受信
socket.on("demo", (data) => {
  console.log(data.user);
  const markdownText = data.user;
  const htmlContent = marked.parse(markdownText);
  h_chatlog.innerHTML += `<div class="user">${htmlContent}</div>`;
  h_chatlog.scrollTop = h_chatlog.scrollHeight;
});

// AIの応答を受信したときの処理
socket.on("ai_response", (data) => {
  if (data.session_id != sessionId)  return;
  const markdownText = data.ai_response;
  const htmlContent = marked.parse(markdownText);
  h_chatlog.innerHTML += `<div class="assistant">${htmlContent}</div>`;
  h_chatlog.scrollTop = h_chatlog.scrollHeight;
});

// 音声を再生する処理
socket.on("play_audio", async (data) => {
  if (data.session_id != sessionId)  return;

  const audioBlob = new Blob([data.audio], { type: "audio/mp3" });
  const audioUrl = URL.createObjectURL(audioBlob);

  const audio = new Audio(audioUrl);


  //画像を口パクさせる
  // clearInterval(blinkInterval); // 瞬き処理を停止
  let isSpeaking = false; // 現在の口パク状態を管理するフラグ
  // let isMouthOpen = false; // 口パク状態を管理するフラグ
  // let blinkcount = 0; // まばたき回数を管理するカウンタ
  let speakingInterval;

  // Web Audio API を使用して音声レベルを解析
  const audioContext = new AudioContext();
  const source = audioContext.createMediaElementSource(audio);
  const analyser = audioContext.createAnalyser();
  analyser.fftSize = 256;

  const dataArray = new Uint8Array(analyser.frequencyBinCount);
  source.connect(analyser);
  analyser.connect(audioContext.destination);

  function updateSpeakingState() {
    analyser.getByteFrequencyData(dataArray);
    const volume = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
    //console.log("Volume:", volume); // デバッグ用


    // 音量が閾値を超えたら口パクを開始、超えなければ停止
    const threshold = 10; // 無音とみなす閾値（調整可能）
    if (volume >= threshold) {
      if (!isSpeaking) {
        isSpeaking = true;
        // 口パクを開始
        speakingInterval = setInterval(() => {
          // if(isMouthOpen) {
          //   if (++blinkcount > 5) {
          //     h_img.src = "/static/Lum_Listening2_blinking.png"; // 無音時の画像
          //     blinkcount = 0; // まばたき回数をリセット
          //   }else {
          //     h_img.src = "/static/Lum_Listening2.png"; // 無音時の画像
          //   }
          //   isMouthOpen = false;
          // }
          // else {
          //   h_img.src = "/static/Lum_Speaking2.png"; // 音声時の画像
          //   isMouthOpen = true;
          // } 
          // h_img.src = h_img.src.includes("Lum_Listening2.png")
          //   ? "/static/Lum_Speaking2.png"
          //   : "/static/Lum_Listening2.png";
          h_img2.hidden = !h_img2.hidden; // 口パクの画像を切り替え
        }, 150);
      }
    } else {
      if (isSpeaking) {
        isSpeaking = false;
        // 口パクを停止
        clearInterval(speakingInterval);
        //h_img.src = "/static/Lum_Listening2.png"; // 無音時の画像
        h_img2.hidden = true; // 口パクの画像を非表示
      }
    }
  }

  // 定期的に音声レベルをチェック
  let levelCheckInterval;
  if(!data.demo) { 
    levelCheckInterval = setInterval(updateSpeakingState, 10);
  } 

  // 音声再生が終了したら処理を停止
  audio.onended = () => {
    if (!data.demo) {
      clearInterval(levelCheckInterval); // 音声レベルチェックを停止
      clearInterval(speakingInterval); // 口パクを停止
      // blinkInterval = setInterval(() => { // 瞬き再開
      //   if (blink++ > blink_threshold) {
      //     h_img.src = "/static/Lum_Listening2_blinking.png"; // 無音時の画像
      //     blink = 0; // まばたき回数をリセット
      //   } else {
      //     h_img.src = "/static/Lum_Listening2.png"; // 無音時の画像
      //   }
      // }, 150);
      // h_img.src = "/static/Lum_Listening2.png"; // 無音時の画像
      h_img2.hidden = true; // 口パクの画像を非表示
    }
    setBtnonRestart();
  };

  audio.play();

});

// AIの応答（テキストのみ）を受信したときの処理
socket.on("ai_textstream", (data) => {
  if (data.session_id != sessionId)  return;
  if (data.sentens.includes("---Start---")) {
    // 最初はdivを作成
    h_chatlog.innerHTML += `<div class="assistant"></div>`;
    const assistantDivs = h_chatlog.getElementsByClassName("assistant");
    currentDiv = assistantDivs[assistantDivs.length - 1]; //作ったdivを取得
    return;
  }
  else if (data.sentens.includes("---End---") ){
    // 終了時はmarkedを適用
    currentDiv.innerHTML= marked.parse(currentDiv.innerHTML);
    currentDiv = ""; //初期化
    h_chatlog.scrollTop = h_chatlog.scrollHeight;
    return;
  }
  else {
    // sentensを追記
    currentDiv.innerHTML += data.sentens;
    h_chatlog.scrollTop = h_chatlog.scrollHeight;
    return;
  } 
});

// AIの応答ストリームを受信したときの処理
socket.on("ai_stream", (data, on_complete) => {
  if (data.session_id != sessionId)  return;

  if (data.sentens) {
    if (data.sentens.includes("---Start---")) {
      // 最初はdivを作成
      h_chatlog.innerHTML += `<div class="assistant"></div>`;
      const assistantDivs = h_chatlog.getElementsByClassName("assistant");
      currentDiv = assistantDivs[assistantDivs.length - 1]; //作ったdivを取得
      return;
    }
    // else if (data.sentens.includes("---End---") ){
    //     // 終了時はmarkedを適用
    //     currentDiv.innerHTML= marked.parse(currentDiv.innerHTML);
    //     currentDiv = ""; //初期化
    //     return;
    // }
    else {
      // sentensをセンテンスキューに登録
      sentensQueue.push(data.sentens);
      if (on_complete) {
        sentensQueue.push(on_complete);
      }
    }
  }

  if (data.audio) {
    // 音声ファイルをキューに登録
    const audioBlob = new Blob([data.audio], { type: "audio/mp3" });
    const audioUrl = URL.createObjectURL(audioBlob);
    audioQueue.push(audioUrl); // オーディオキューに登録

    if (!isPlaying) {
      playAudioWithSentens();
    }
  }
});

// Queueに登録された音声ファイルを再生するとともにテキストも表記していく処理
async function playAudioWithSentens() {
  // 再生する音声ファイルがなければ終了
  if (audioQueue.length === 0) {
    isPlaying = false;
    //もしセンテンスQueにデータがあれば全部吐き出す
    while (sentensQueue.length) {
      const sentens = sentensQueue.shift();
      if (sentens.includes("---End---")) { // 終了のメッセージを受け取ったら
        currentDiv.innerHTML = marked.parse(currentDiv.innerHTML);
        h_chatlog.scrollTop = h_chatlog.scrollHeight;
        currentDiv = ""; //初期化
        complete=sentensQueue.shift(); // 処理完了を通知
        complete();
      } else {
        currentDiv.innerHTML += sentens;
        h_chatlog.scrollTop = h_chatlog.scrollHeight;
      }
    }
    setBtnonRestart();
    return;
  }
  // 再生中フラグを立てる
  isPlaying = true;

  //AudioQueueから音声ファイルを取り出し
  const audioUrl = audioQueue.shift();
  const audio = new Audio(audioUrl);

  //SentensQueueからセンテンスを取り出して表示
  //ただし---silent---が含まれている場合は表示しない
  const sentens = sentensQueue.shift();
  if (!sentens.includes("---silent---")) {
    // センテンスを表示
    // ここに音声の長さ に応じて１文字ずつ表示させる処理を追加する
    //currentDiv.innerHTML += sentens;

    //音声の時間長を取得
    audio.addEventListener("loadedmetadata", () => {
      // 音声の長さに応じてセンテンスを表示する
      const duration = audio.duration; // 音声の長さ（秒）
      const words = sentens
      const interval = duration / words.length; // １文字ごとの表示間隔

      let index = 0;
      const displayInterval = setInterval(() => {
        if (index < words.length) {
          currentDiv.innerHTML += words[index];
          index++;
        } else {
          clearInterval(displayInterval);
        }
      }, interval * 1000); // ミリ秒に変換
    });
    h_chatlog.scrollTop = h_chatlog.scrollHeight;
  }



  //画像を口パクさせる
  // clearInterval(blinkInterval); // 瞬き処理を停止
  let isSpeaking = false; // 現在の口パク状態を管理するフラグ
  // let isMouthOpen = false; // 口パク状態を管理するフラグ
  // let blinkcount = 0; // まばたき回数を管理するカウンタ
  let speakingInterval;

  // Web Audio API を使用して音声レベルを解析
  const audioContext = new AudioContext();
  const source = audioContext.createMediaElementSource(audio);
  const analyser = audioContext.createAnalyser();
  analyser.fftSize = 256;

  const dataArray = new Uint8Array(analyser.frequencyBinCount);
  source.connect(analyser);
  analyser.connect(audioContext.destination);

  function updateSpeakingState() {
    analyser.getByteFrequencyData(dataArray);
    const volume = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
    //console.log("Volume:", volume); // デバッグ用


    // 音量が閾値を超えたら口パクを開始、超えなければ停止
    const threshold = 10; // 無音とみなす閾値（調整可能）
    if (volume >= threshold) {
      if (!isSpeaking) {
        isSpeaking = true;
        // 口パクを開始
        speakingInterval = setInterval(() => {
          // if(isMouthOpen) {
          //   if (++blinkcount > 5) {
          //     h_img.src = "/static/Lum_Listening2_blinking.png"; // 無音時の画像
          //     blinkcount = 0; // まばたき回数をリセット
          //   }else {
          //     h_img.src = "/static/Lum_Listening2.png"; // 無音時の画像
          //   }
          //   isMouthOpen = false;
          // }
          // else {
          //   h_img.src = "/static/Lum_Speaking2.png"; // 音声時の画像
          //   isMouthOpen = true;
          // } 
          // h_img.src = h_img.src.includes("Lum_Listening2.png")
          //   ? "/static/Lum_Speaking2.png"
          //   : "/static/Lum_Listening2.png";
          h_img2.hidden = !h_img2.hidden; // 口パクの画像を切り替え
        }, 150);
      }
    } else {
      if (isSpeaking) {
        isSpeaking = false;
        // 口パクを停止
        clearInterval(speakingInterval);
        // h_img.src = "/static/Lum_Listening2.png"; // 無音時の画像
        h_img2.hidden = true; // 口パクの画像を非表示
      }
    }
  }

  // 定期的に音声レベルをチェック
  const levelCheckInterval = setInterval(updateSpeakingState, 10);

  // 再生が終了したら次の音声ファイルを再生
  audio.onended = () => {
    clearInterval(levelCheckInterval); // 音声レベルチェックを停止
    clearInterval(speakingInterval); // 口パクを停止
    // blinkInterval = setInterval(() => { // 瞬き再開
    //   if (blink++ > blink_threshold) {
    //     h_img.src = "/static/Lum_Listening2_blinking.png"; // 無音時の画像
    //     blink = 0; // まばたき回数をリセット
    //   } else {
    //     h_img.src = "/static/Lum_Listening2.png"; // 無音時の画像
    //   }
    // }, 150);
    // h_img.src = "/static/Lum_Listening2.png"; // 無音時の画像
    h_img2.hidden = true; // 口パクの画像を非表示

    playAudioWithSentens();
  };

  audio.play();

}

// WebSpeechAPIの音声認識
function startSpeechRecognition() {
  if (!("webkitSpeechRecognition" in window)) {
    alert("Web Speech APIはこのブラウザではサポートされていません");
    return;
  }

  // 音声認識の設定
  const lang = document.querySelector('input[name="languageCode"]:checked').value;
  recognition = new webkitSpeechRecognition();
  recognition.lang = lang; // 言語設定
  recognition.interimResults = true; // 途中結果を取得
  recognition.continuous = true; // 連続認識（文が確定しても続ける）

  // Chatlogの末尾にuserクラスのdivを追加
  const div = document.createElement("div");
  div.classList.add("user");
  h_chatlog.appendChild(div);
  const h_lastElement = h_chatlog.lastElementChild;

  // Chatlogの末尾の要素に途中結果を表示するdivを追加
  const divInterrim = document.createElement("div");
  divInterrim.id = "interim";
  h_chatlog.appendChild(divInterrim);
  const h_interim = h_chatlog.lastElementChild;

  //　イベントリスナー
  // 音声認識が成功したときの処理
  recognition.onresult = (event) => {
    let interimText = "";
    let finalText = "";

    for (let i = 0; i < event.results.length; i++) {
      const result = event.results[i];

      if (result.isFinal) {
        // 確定した文（確定後に漢字変換などが反映される）
        finalText += result[0].transcript + " ";
        h_lastElement.innerText = finalText;
        h_interim.innerText = "";
      } else {
        // 途中結果（リアルタイム表示用）
        interimText += result[0].transcript;
        h_interim.innerText = interimText;
      }
    }
    // 途中結果を表示
  };

  // 音声認識がエラーになったときの処理
  recognition.onerror = (event) => {
    console.error("認識エラー:", event.error);
  };

  // 音声認識が終了したときの処理
  recognition.onend = () => {
    console.log("音声認識が終了しました");
    // formデータを取得
    const formData = new FormData(document.getElementById("myForm"));
    console.log(formData);
    getFormValues();

    // 音声ファイルを追加
    finalText = h_lastElement.innerText;
    formData.append("text", finalText);

    // fetch先を指定
    const method = document.querySelector('input[name="Method"]:checked').value;

    fetch(method, {
      method: "POST",
      headers: {
        "X-Session-ID": sessionId  // タブごとに異なるIDを送信
      },
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        console.log(data);
        // ボタン状態の初期化
        setBtnonRestart();
      })
      .catch((error) => {
        console.error("Upload failed:");
        // ボタン状態の初期化
        setBtnonRestart();
      });
  };

  // 音声認識を開始
  recognition.start();
}

// 音声認識を停止
function stopRecognition() {
  if (recognition) {
    recognition.stop();
    //interimのdivを削除
    const h_interim = document.getElementById("interim");
    h_interim.remove();
  }
}


/********* HTML の　Interface ********** */
// InputModelの選択による表示切り替え
h_radioTextInput.addEventListener("click", () => {
  document.getElementById("divSpeechRecognitionConfig").hidden = true;
  document.getElementById("divTextInputArea").hidden = false;
  document.getElementById("divStartStopBtn").hidden = true;
});
h_radioVoiceInput.addEventListener("click", () => {
  document.getElementById("divSpeechRecognitionConfig").hidden = false;
  document.getElementById("divTextInputArea").hidden = true;
  document.getElementById("divStartStopBtn").hidden = false;

});

// OutputModelの選択による表示切り替え
h_radioTextOutput.addEventListener("click", () => {
  document.getElementById("divTTSConfig").hidden = true;
});
h_radioVoiceOutput.addEventListener("click", () => {
  document.getElementById("divTTSConfig").hidden = false;
});



// スピードの値を表示
h_rangeSpeed.addEventListener("input", () => {
  h_spanSpeedValue.textContent = h_rangeSpeed.value;
});

// 高さの値を表示
h_rangePitch.addEventListener("input", () => {
  h_spanPitchValue.textContent = h_rangePitch.value;
});

// 抑揚の値を表示
h_rangeIntonation.addEventListener("input", () => {
  h_spanIntonationValue.textContent = h_rangeIntonation.value;
});

// TTSselectの選択による表示切り替え
// もしVoiceVoxが選択されていたら，画像をListening.png, Speaking.pngに変更する。
h_radioVoicevoxTTS.addEventListener("click", () => {
  document.getElementById("divVoiceVoxSpeaker").hidden = false;
  // document.getElementById("divGoogleSpeaker").hidden = true;
  h_img.src = "/static/Listening.png";
  h_img2.src = "/static/Speaking.png";
  h_img3.src = "/static/Listening.png";
});

//// もしGoogleTTSが選択されていたら，画像をLum1.png, Lum2.png, Lum_Blinking.pngに変更する。
h_radioGPTSoVITS.addEventListener("click", () => {
  document.getElementById("divVoiceVoxSpeaker").hidden = true;
  // document.getElementById("divGoogleSpeaker").hidden = false;
  h_img.src = "/static/Lum1.png";
  h_img2.src = "/static/Lum2.png";
  h_img3.src = "/static/Lum_blink.png";
});

// GoogleTTSの言語選択による表示切り替え
//// もし日本語が選択されていたら，JPvoiceSelectを表示し，ENvoiceSelectを非表示にする
document.getElementById("langCode_jp").addEventListener("click", () => {
  document.getElementById("radioVoicevoxTTS").hidden = false;
  document.getElementById("JPvoiceSelect").hidden = false;
  document.getElementById("ENvoiceSelect").hidden = true;
});
//// もし英語が選択されていたら，JPvoiceSelectを非表示し，ENvoiceSelectを表示する
document.getElementById("langCode_en").addEventListener("click", () => {
  document.getElementById("radioVoicevoxTTS").hidden = true;
  h_radioGPTSoVITS.click();
  document.getElementById("JPvoiceSelect").hidden = true;
  document.getElementById("ENvoiceSelect").hidden = false;
});

// Spaceキーが押されたときにstartRecordingボタンをクリック
document.addEventListener("keydown", (event) => {
  // テキスト入力モードの時は無効
  if(h_radioTextInput.checked){
    return;
  }
  if (h_btnStartRec.disabled) {
    console.log("処理中のため入力はできません");
    return;
  }
  if (event.code === "Space" && !event.repeat) {
    h_btnStartRec.click();
  }
});

// Spaceキーから指が離されたときにstopRecordingボタンをクリック
document.addEventListener("keyup", (event) => {
  // テキスト入力モードの時は無効
  if(h_radioTextInput.checked){
    return;
  }
  if (h_btnStopRec.disabled) {
    console.log("不正な録音停止操作です");
    return;
  }
  if (event.code === "Space" && !event.repeat) {
    h_btnStopRec.click();
  }
});

// chatInputTextの入力中にCtrl＋Enterが押されたときにh_btnChatTextInputをクリック
h_chatTextInputArea.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.key === "Enter") {
    h_chatTextInputArea.disabled = true; // 入力エリアを無効化
    h_btnChatTextInput.click();
  }
});

/***************** 
 * VoiceChatのコア部分の処理　 
 * **************** */

//Speakerの音声確認テスト
h_btnSpeakerTest.addEventListener("click", () => {
  const formData = new FormData(document.getElementById("myForm"));

  fetch("/speaker_test", {
    method: "POST",
    headers: {
      "X-Session-ID": sessionId  // タブごとに異なるIDを送信
    },
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
    });
});

// 聞き取りスタートボタンがクリックされたときの処理
h_btnGetFQ.addEventListener("click", () => {
  h_btnGetFQ.disabled = true; // 聞き取りスタートボタンを無効化
  fetch("/start_listening", {
    method: "POST",
    headers: {
      "X-Session-ID": sessionId  // タブごとに異なるIDを送信
    },
    body: new FormData(document.getElementById("myForm"))
  })
  .then(response => response.json())
  .then(data => {
    console.log(data);
    if (data.message) {
      const markdownText = data.message;
      const htmlContent = marked.parse(markdownText);
      h_chatlog.innerHTML += `<div class="assistant">${htmlContent}</div>`;
      h_chatlog.scrollTop = h_chatlog.scrollHeight;
    }
    
    setBtnonRestart();

  })
  .catch(error => {
    console.error("Error starting listening:", error);
  });
});

// 録音開始ボタンがクリックされたときの処理
h_btnStartRec.addEventListener("click", () => {
  audioContext = new AudioContext();
  const source = audioContext.createMediaStreamSource(window.stream);
  recorder = new Recorder(source, { numChannels: 1 }); // モノラル録音
  recorder.record();

  const h_SpeechRecog = document.querySelector(
    'input[name="SpeechRecognition"]:checked'
  );
  //WebSpeechAPIを使うなら音声認識を開始
  if (h_SpeechRecog.value === "WebSpeechAPI") {
    startSpeechRecognition();
    console.log("WebSpeechAPIを開始しました");
  } else {
    console.log("音声認識はサーバーサイドで行ないます");
  }

  // ボタンを無効化
  setBtnonStart();
});

/************* 送信処理 ********************/
// 録音停止ボタンがクリックされたときの処理
h_btnStopRec.addEventListener("click", () => {
  // ボタンを無効化
  setBtnunderProcessing();

  // 録音を停止
  recorder.stop();

  //WebSpeechAPIの時は音声認識を停止
  const h_SpeechRecog = document.querySelector(
    'input[name="SpeechRecognition"]:checked'
  );
  if (h_SpeechRecog.value === "WebSpeechAPI") {
    //音声認識処理の停止と送信はまとめて以下の関数で実施
    stopRecognition();
  }
  //
  else {
    console.log("音声認識はサーバーサイドで行ないます");
    // 音声ファイルを作成⇒作成が済んだらコールバック関数実行
    recorder.exportWAV((blob) => {
      audioBlob = blob;
      if (!audioBlob) {
        console.error("No audio to upload");
        return;
      }

      // formデータを取得
      const formData = new FormData(document.getElementById("myForm"));
      console.log(formData);
      getFormValues();

      // 音声ファイルを追加
      formData.append("file", audioBlob, "recorded_audio.wav");

      // fetch先を指定
      const method = document.querySelector(
        'input[name="Method"]:checked'
      ).value;

      fetch(method, {
        method: "POST",
        headers: {
          "X-Session-ID": sessionId  // タブごとに異なるIDを送信
        },          
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          console.log(data);
          //テキスト出力モードのときはここで
          // ボタン状態の初期化
          if(h_radioTextOutput.checked){
            setBtnonRestart();
          }
        })
        .catch((error) => {
          console.error("Upload failed:");
          // ボタン状態の初期化
          setBtnonRestart();
        });
    });
  }

  // 録音した音声をファイルに保存して送信
});

// テキスト入力モードでチャット送信ボタンがクリックされたときの処理
h_btnChatTextInput.addEventListener("click", () => {
  const formData = new FormData(document.getElementById("myForm"));

  // テキストを追加
  inputText = h_chatTextInputArea.value;//document.getElementById("chatInputText").value;
  formData.append("text", inputText);

  // チャットログに追加
  h_chatlog.innerHTML += `<div class="user">${inputText}</div>`;
  h_chatlog.scrollTop = h_chatlog.scrollHeight;    

  const formDataObj = Object.fromEntries(formData.entries());
  console.log(formDataObj);

  // fetch先を指定
  const method = document.querySelector('input[name="Method"]:checked').value;

  fetch(method, {
    method: "POST",
    headers: {
      "X-Session-ID": sessionId  // タブごとに異なるIDを送信
    },
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      h_chatTextInputArea.value = "";      // テキストエリアを初期化
      h_chatTextInputArea.disabled = false; // 入力エリアを有効化

    })
    .catch((error) => {
      console.error("Upload failed:");
      // ボタン状態の初期化
    });
});

// デモモードの起動
document.getElementById("btnDemo").addEventListener("click", () => {
  document.getElementById("btnDemo").disabled = true;
  const formData = new FormData(document.getElementById("myForm"));

  // チャットログに追加
  h_chatlog.innerHTML += `<div>デモモードを開始します</div>`;
  h_chatlog.scrollTop = h_chatlog.scrollHeight;

  //FormDataのログ出力
  const formDataObj = Object.fromEntries(formData.entries());
  console.log(formDataObj);

  // fetch先を指定
  const method = "demo"

  // fetchを実行
  fetch(method, {
    method: "POST",
    headers: {
      "X-Session-ID": sessionId  // タブごとに異なるIDを送信
    },
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      // ボタン状態の初期化
      document.getElementById("btnDemo").disabled = false;
    })
    .catch((error) => {
      console.error("Upload failed:");
      // ボタン状態の初期化
      document.getElementById("btnDemo").disabled = false;
    });
});

// デモモードの停止
document.getElementById("btnDemoStop").addEventListener("click", () => {
  // チャットログに追加
  h_chatlog.innerHTML += `<div>デモモードを終了します</div>`;
  h_chatlog.scrollTop = h_chatlog.scrollHeight;

  // fetchを実行
  fetch("demo_stop", {
    method: "POST",
    headers: {
      "X-Session-ID": sessionId  // タブごとに異なるIDを送信
    }
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      // ボタン状態の初期化
    })
    .catch((error) => {
      console.error("Upload failed:");
      // ボタン状態の初期化
      document.getElementById("btnDemo").disabled = false;
    });
});



  /***** Event listener *****/
document.addEventListener("DOMContentLoaded", () => {
  // ボタン状態の初期化
  setBtnonRestart();
  h_btnStartRec.disabled = true; // 録音開始ボタンを無効化

  // まばたき処理
  let blink = 0; // まばたきさせるための待ち回数カウンタ
  let blink_threshold = 30; // まばたきさせるための待ち回数
  let blinkInterval = null; // 瞬き処理のインターバルID
  blinkInterval = setInterval(() => {
    if (blink++ > blink_threshold) {
      h_img3.hidden = false; // 画像を表示
      blink = 0; // まばたき回数をリセット
      blink_threshold = Math.floor(Math.random() * 30)+1 ; // 1～30のランダム値
    } else {
      h_img3.hidden= true; // 画像を非表示
    }
  }, 150);
});

// ページを離れるときにストリームを停止
window.addEventListener("beforeunload", () => {
  if (window.stream) {
    window.stream.getTracks().forEach((track) => {
      track.stop();
    });
  }
  clearInterval(blinkInterval); // 瞬き処理を停止
  navigator.sendBeacon("/logout", JSON.stringify({ session_id: sessionStorage.getItem("session_id") }));  
});
