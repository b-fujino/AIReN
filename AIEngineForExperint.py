'''
AIEngineForExperint.py

実験用のAIエンジン．シングルプロンプトでインタビュワーがインタビューを行っていく．
'''
import json
import time
import os
from pprint import pprint # 辞書形式のものを整えて出力する．

from systemprompt_Agent_Experiment import INTERVIEWER_no_Guided, INTERVIEWER_Guided
from systemprompt_Agent_Summarizer import SUMMARIZER_PRIMARY
from systemprompt_Agent_ReportGenerater import REPORT_GENERATER_J
from systemprompt_Reporter import REPORTER_J, SCENARIO_J_1, SCENARIO_J_2 , SCENARIO_J_3, SCENARIO_J_4, SCENARIO_J_5
from systemprompt_IncidentReportGuide_Pydantic import IncidentReport_J as format_Report
from AIEngineCore import AIReNTest

from call_openai_api_Ollama import Agent_chat, Agent_chat_parsed, Agent_chat_tools
#from call_openai_api_openai import Agent_chat, Agent_chat_parsed

from pydantic import BaseModel, Field

class CheckNewInfoModel(BaseModel):
    is_NewInfo: bool = Field(description="もし新しい情報が含まれていたら, true; もし特に新しい情報が含まれていなければ, false.")

# directory_pathの設定"
output_dir =  f"Study_Output/Run_NoAIReN_{time.strftime('%Y%m%d_%H%M%S')}"
os.makedirs(output_dir, exist_ok=True)

if __name__ == "__main__":

    threshold = 3 # 新しい情報が含まれていないと判断された場合のカウントの閾値．この数以上になったらインタビューを終了する．

    for exp_num in range(0, 10): # 実験の繰り返し回数．必要に応じて変更する．

        # シナリオを1～5まで，順に実行する．
        for idx, scenario in enumerate([SCENARIO_J_1, SCENARIO_J_2 , SCENARIO_J_3, SCENARIO_J_4, SCENARIO_J_5], start=1):
            SCENARIO_J = scenario


            for experiment in range(0, 2):
                experiment = "INTERVIEWER_no_Guided" if experiment % 2 == 1 else "INTERVIEWER_Guided"

                if experiment == "INTERVIEWER_no_Guided":
                    INTERVIEWER = INTERVIEWER_no_Guided
                    fileName = "NoGuided" # "NoGuided" # ファイル名に使用する．
                elif experiment == "INTERVIEWER_Guided":
                    INTERVIEWER = INTERVIEWER_Guided
                    fileName = "Guided"

                """対話ログを残すファイル名の例：SCENARIO_1_Ollama_INTERVIEWER_no_Guided_turn_1_chatlog_20240620_153000.txt"""
                filename_chatlog = f"{output_dir}/SCENARIO_{idx}_Ollama_{fileName}_turn_{exp_num}_chatlog_{time.strftime('%Y%m%d_%H%M%S')}.txt"

                count = 0 # 新しい情報が含まれていないと判断された場合のカウント．

                # 3. インタビューの実行
                ## 3.1 インタビュワーからの最初の質問の生成
                chatlog4interviewer = [{"role": "user", "content": "はじめまして．ヒヤリハットの報告に来ました．"}]
                Question = Agent_chat(
                    system_prompt=INTERVIEWER,
                    messages=chatlog4interviewer
                )

                turn = 1 # ターン数のカウント．最初の質問がターン1．以降、インタビュワーが質問するたびにターン数を増やす．
                print(f"## turn{turn}")
                print(f"Question:{Question}")
                with open(filename_chatlog, "w", encoding="utf-8") as f: # チャットログのファイルを新規作成して、最初の質問を書き込む．以降は追記モードで書き込む．
                    f.write(f"# turn{turn}\n")
                    f.write(f"## Question:\n{Question}\n\n")

                chatlog4interviewer.append({"role": "assistant", "content": Question})
                chatlog4reporter = [{"role": "user", "content": Question}]   
                summary = []
                ## 3.2 ループ処理
                while True:
                    ### 3.2.1 レポーターからの回答の生成
                    Answer = Agent_chat(
                        system_prompt=REPORTER_J + f"\n\n[Scenario]: {json.dumps(SCENARIO_J, ensure_ascii=False)}",
                        messages=chatlog4reporter
                    )

                    print(f"Answer:{Answer}")
                    with open(filename_chatlog, "a", encoding="utf-8") as f:
                        f.write(f"## Answer:\n{Answer}\n\n")

                    ### 3.2.2 新しい情報が含まれているかの判定
                    CheckNewInfo = Agent_chat_parsed(
                        system_prompt = f"あなたはコンテンツを分析し、新しい情報が含まれているかどうかを判断するエキスパートです。logの内容に対して，NewAnswerの内容が新しい情報を含んでいるかどうかを、is_NewInfoにtrue/falseで答えてください。",
                        messages = [{"role": "user", "content": f"[log]：{chatlog4reporter}\n\n [NewAnswer]: {Answer}"}],
                        format=CheckNewInfoModel
                    )
                    if not CheckNewInfo.is_NewInfo: # 新しい情報が含まれていないと判断されたらカウントを増やす．
                        count+=1
                    else:
                        count=0 # 新しい情報が含まれていると判断されたらカウントをリセットする．

                    ### 3.2.3 カウントが一定数以上であればインタビューの終了．
                    if count >= threshold:
                        print("インタビューを終了します。")
                        print(f"最終的なSummary:")
                        for i, smry in enumerate(summary):
                            print(f"{i+1}. {smry}")
                        break


                    ### 3.2.4 サマリー作成
                    smry = Agent_chat(
                        system_prompt=SUMMARIZER_PRIMARY,
                        messages=[
                            {"role": "user", "content": f"[Question]\n{Question}\n\n[Answer]\n{Answer}"},
                        ],
                        temperature=0.0,
                    )
                    print(f"AI SUMMARIZER: ")
                    print(smry)
                    with open(filename_chatlog, "a", encoding="utf-8") as f:
                        f.write(f"## AI SUMMARIZER:\n{smry}\n\n")
                    summary.append(smry)

                    ### 3.2.5 回答の記録
                    chatlog4interviewer.append({"role": "user", "content": Answer})
                    chatlog4reporter.append({"role": "assistant", "content": Answer})

                    ### 3.2.6 インタビュワーからの次の質問の生成
                    Question = Agent_chat(
                        system_prompt=INTERVIEWER,
                        messages=chatlog4interviewer
                    )

                    turn += 1
                    print(f"## turn{turn}")
                    print(f"Question:{Question}")
                    with open(filename_chatlog, "a", encoding="utf-8") as f:
                        f.write(f"# turn{turn}\n")
                        f.write(f"## Question:\n{Question}\n\n")
                    chatlog4interviewer.append({"role": "assistant", "content": Question})
                    chatlog4reporter.append({"role": "user", "content": Question})

                # 4. 最終要約の生成
                summary_text = "[SUMMARY]\n" + "\n".join(summary)
                summary_json = Agent_chat_parsed( # Generate summary
                    messages=[{"role": "user", "content": summary_text}],
                    system_prompt=REPORT_GENERATER_J,
                    format= format_Report,
                )

                output = f"AI SUMMARY:\n{summary_json.model_dump_json(ensure_ascii=False, indent=2)}\n"; 
                print(output);
                # 5. 結果のファイルへの出力
                with open(f"{output_dir}/SCENARIO_{idx}_Ollama_{fileName}_turn_{exp_num}_{time.strftime('%Y%m%d_%H%M%S')}.json", "w", encoding="utf-8") as f:
                   f.write(summary_json.model_dump_json(ensure_ascii=False, indent=2))

    for _ in range(0, 10): # 実験の繰り返し回数．必要に応じて変更する．    
        AIReNTest(bSTREAM=False) # AIReNTestを呼び出して実験を実行する。AIReNTestの中で全シナリオ回される



        
