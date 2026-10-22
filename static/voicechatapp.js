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


/***** 口パク（リップシンク） *****/
// 再生中の音声の音量から口の開き具合(0～1)を求め，毎フレーム滑らかに追従させる．
// アバター画像ごとに口の動かし方を切り替える（キーは画像ファイル名）
//  draw : 口を開いた差分画像がないので，canvasに口を描画する（座標は元画像のピクセル座標）
//  blend: 位置の揃った「口を開いた画像」(image2)を開き具合に応じた不透明度で重ねる
const LIPSYNC_AVATARS = {
  // skew: 口の開きが最も深くなる位置（-1～1，負で向かって左）．顔が向かって左を向いているので左に寄せる
  "Listening.png": { mode: "draw", mouth: { cx: 584, cy: 279, w: 54, curve: 4.0, maxOpen: 20, skew: -0.3 } },
  "Lum1.png": { mode: "blend" },
};
const LIPSYNC = {
  noiseFloor: 0.01, // これ以下の音量(RMS)は口を閉じる
  range: 0.12,      // noiseFloor + range の音量で全開
  attack: 0.5,      // 開くときの追従率（1フレームあたり）
  release: 0.2,     // 閉じるときの追従率（開くより遅くして自然に）
};

let lipAudioContext = null; // 口パク用のAudioContext（1つを使い回す）
let lipAnalyser = null;
let lipBuffer = null;
const lipAudios = new Set(); // 口パクの解析対象の音声
let mouthOpen = 0;       // 現在の口の開き具合 0～1

// 口を描画するcanvasをimage1の上に重ねる
const h_mouthCanvas = document.createElement("canvas");
h_mouthCanvas.id = "mouthCanvas";
h_mouthCanvas.style.position = "absolute";
h_mouthCanvas.style.zIndex = 2;
h_mouthCanvas.style.pointerEvents = "none";
h_img.insertAdjacentElement("afterend", h_mouthCanvas);

function currentAvatar() {
  return LIPSYNC_AVATARS[decodeURIComponent(h_img.src.split("/").pop())] || null;
}

// image1の中で実際に絵が描かれている矩形（object-fit: contain の余白を除く）
function avatarContentRect() {
  const cw = h_img.clientWidth, ch = h_img.clientHeight;
  const nw = h_img.naturalWidth, nh = h_img.naturalHeight;
  if (!cw || !ch || !nw || !nh) return null;
  const s = Math.min(cw / nw, ch / nh);
  return { x: h_img.offsetLeft + (cw - nw * s) / 2, y: h_img.offsetTop + (ch - nh * s) / 2, w: nw * s, h: nh * s, s: s };
}

// canvas・口を開いた画像・まばたき画像をimage1の絵にぴったり重ねる
function layoutAvatar() {
  const r = avatarContentRect();
  if (!r) return;
  for (const el of [h_mouthCanvas, h_img2, h_img3]) {
    el.style.left = r.x.toFixed(2) + "px";
    el.style.top = r.y.toFixed(2) + "px";
    el.style.width = r.w + "px";
    el.style.maxWidth = "none";
    el.style.maxHeight = "none";
  }
  h_mouthCanvas.style.height = r.h + "px";
  h_img2.style.height = r.h + "px";
  h_img3.style.height = "auto"; // まばたき画像は上部だけの切り抜きのことがある
  const dpr = window.devicePixelRatio || 1;
  h_mouthCanvas.width = Math.round(r.w * dpr);
  h_mouthCanvas.height = Math.round(r.h * dpr);
  renderMouth(mouthOpen);
}

// canvasに開き具合aの口を描く
function drawMouth(a, avatar) {
  const ctx = h_mouthCanvas.getContext("2d");
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, h_mouthCanvas.width, h_mouthCanvas.height);
  const r = avatarContentRect();
  if (a < 0.03 || !r || !avatar || avatar.mode !== "draw") return;

  const m = avatar.mouth;
  const k = r.s * (window.devicePixelRatio || 1);
  ctx.setTransform(k, 0, 0, k, 0, 0); // 以降は元画像のピクセル座標で描く

  const w = m.w * (1 - 0.15 * a); // 開くほど少しすぼめる
  const h = m.maxOpen * a;
  const p = m.skew || 0;
  // 両端で0，t=pで1になる開き方の形
  const profile = (t) => {
    const u = t < p ? (t - p) / (1 + p) : (t - p) / (1 - p);
    return Math.max(0, 1 - u * u);
  };
  const n = 24;
  const top = [], bot = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n * 2 - 1; // -1～1
    const x = m.cx + t * w / 2;
    const smile = m.curve * (1 - t * t); // 口角の上がった笑みの弧
    top.push([x, m.cy + smile * (1 - 0.6 * a) - h * 0.15 * profile(t)]);
    bot.push([x, m.cy + smile + h * Math.pow(profile(t), 0.8)]);
  }

  // 口の中
  ctx.beginPath();
  ctx.moveTo(top[0][0], top[0][1]);
  for (const p of top) ctx.lineTo(p[0], p[1]);
  for (let i = bot.length - 1; i >= 0; i--) ctx.lineTo(bot[i][0], bot[i][1]);
  ctx.closePath();
  ctx.fillStyle = "rgb(110, 40, 45)";
  ctx.fill();

  // 舌（口の形で切り抜く）
  const by = Math.max(...bot.map((p) => p[1]));
  ctx.save();
  ctx.clip();
  ctx.beginPath();
  ctx.ellipse(m.cx + p * w / 2, by - h * 0.025, m.w * 0.3, h * 0.425, 0, 0, 2 * Math.PI);
  ctx.fillStyle = "rgb(220, 120, 120)";
  ctx.fill();
  ctx.restore();

  // 上唇の線
  ctx.beginPath();
  ctx.moveTo(top[0][0], top[0][1]);
  for (const p of top) ctx.lineTo(p[0], p[1]);
  ctx.strokeStyle = "rgb(90, 30, 35)";
  ctx.lineWidth = 1.6;
  ctx.lineCap = "round";
  ctx.stroke();
}

function renderMouth(a) {
  const avatar = currentAvatar();
  drawMouth(a, avatar);
  const opacity = avatar && avatar.mode === "blend" ? Math.min(1, a * 1.4) : 0;
  h_img2.style.opacity = opacity;
  h_img2.hidden = opacity <= 0.02;
}

// 再生する音声を口パクの解析対象にする
function attachLipSync(audio) {
  if (!lipAudioContext) {
    lipAudioContext = new AudioContext();
    lipAnalyser = lipAudioContext.createAnalyser();
    lipAnalyser.fftSize = 1024;
    lipBuffer = new Float32Array(lipAnalyser.fftSize);
    lipAnalyser.connect(lipAudioContext.destination);
  }
  if (lipAudioContext.state === "suspended") lipAudioContext.resume();

  const source = lipAudioContext.createMediaElementSource(audio);
  source.connect(lipAnalyser);
  lipAudios.add(audio);
  const finish = () => {
    if (!lipAudios.delete(audio)) return;
    source.disconnect();
  };
  audio.addEventListener("ended", finish);
  audio.addEventListener("error", finish);
}

// 毎フレーム，音量から目標の開き具合を求めて滑らかに追従させる
function lipSyncLoop() {
  let target = 0;
  // 再生がブロックされた場合などもあるので，実際に再生中の音声があるかで判定する
  if (lipAnalyser && [...lipAudios].some((a) => !a.paused)) {
    lipAnalyser.getFloatTimeDomainData(lipBuffer);
    let sum = 0;
    for (let i = 0; i < lipBuffer.length; i++) sum += lipBuffer[i] * lipBuffer[i];
    const rms = Math.sqrt(sum / lipBuffer.length);
    target = Math.pow(Math.min(1, Math.max(0, (rms - LIPSYNC.noiseFloor) / LIPSYNC.range)), 0.7);
  }
  const rate = target > mouthOpen ? LIPSYNC.attack : LIPSYNC.release;
  const next = mouthOpen + (target - mouthOpen) * rate;
  const changed = Math.abs(next - mouthOpen) > 0.002 || (next < 0.03) !== (mouthOpen < 0.03);
  mouthOpen = next < 0.001 ? 0 : next;
  if (changed) renderMouth(mouthOpen);
  requestAnimationFrame(lipSyncLoop);
}

h_img.addEventListener("load", layoutAvatar); // アバター画像の切り替え時
new ResizeObserver(layoutAvatar).observe(h_img);
layoutAvatar();
requestAnimationFrame(lipSyncLoop);


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
socket.on("play_audio", async (data,complete) => {
  if (data.session_id != sessionId)  return;

  const audioBlob = new Blob([data.audio], { type: "audio/mp3" });
  const audioUrl = URL.createObjectURL(audioBlob);

  const audio = new Audio(audioUrl);


  //音量に応じて口を動かす（デモの報告者の音声ではAIの口は動かさない）
  if (!data.demo) attachLipSync(audio);

  // 音声再生が終了したら処理を完了
  audio.onended = () => {
    if(complete) complete(); // 処理完了を通知
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



  //音量に応じて口を動かす
  attachLipSync(audio);

  // 再生が終了したら次の音声ファイルを再生
  audio.onended = () => {
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
    if (event.error === "network") {
      // WebSpeechAPIはブラウザがGoogleのサーバーで認識するため，ネットにつながっていないと失敗する
      alert("WebSpeechAPIの音声認識に失敗しました（ネットワークエラー）．音声認識エンジンを「サーバーサイド処理」にしてください．");
    }
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
  h_img3.src = "/static/Lum2_blink.png";
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

// オフラインモードではWebSpeechAPI（Googleのサーバーで認識）が使えないので，サーバーサイド処理に固定する
fetch("/config")
  .then((response) => response.json())
  .then((config) => {
    if (config.mode !== "offline") return;
    const h_webSpeech = document.getElementById("radioWebSpeechAPI");
    h_webSpeech.disabled = true;
    document.querySelector('label[for="radioWebSpeechAPI"]').textContent = "WebSpeechAPI（オフラインでは使用不可）";
    document.getElementById("radioServerProcess").checked = true;
  })
  .catch((error) => console.error("設定の取得に失敗しました:", error));
