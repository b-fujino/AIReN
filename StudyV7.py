import json
import time
import re
from pprint import pprint # 辞書形式のものを整えて出力する．


from systemprompt_Agent import INTERVIEWER_J, SUPERVISOR_J #, ELABORATOR_J, SUMMARIZER_J, PROOFWRITER, CHECKER
from systemprompt_Reporter import SCENARIO_J_2 as SCENARIO_J, REPORTER_J
from systemprompt_InterviewGuide_V2 import INTERVIEW_GUIDE_J as INTERVIEW_GUIDE
from systemprompt_IncidentReportGuide import format_Report_J as format_Report

from call_openai_api_Ollama import Agent_chat, Agent_chat_parsed, Agent_chat_tools
#from call_openai_api import Agent_chat, Agent_chat_parsed, Agent_chat_tools
#from call_openai_api_Groq import Agent_chat, Agent_chat_parsed, Agent_chat_tools


from pydantic import BaseModel, Field

class CheckSimilarity(BaseModel):
    is_similar: bool = Field(description="もし意味が同じなら, true; もし意味が違っていたら, false.")


# class JudgeAndInstruct_E(BaseModel):
#     go_next: bool = Field(description="If you think 'go ahead', true; if you think 'stay and follow your instruction', false.")
#     instruct: list[str] = Field(description="Instructions based on the situation. An array with 1 to 3 elements.", max_items=3, min_items=1)
#     model_config = {
#         "description": "Return a 'go_next' and 'instruct' as an answer to the user's input.",
#     }

class JudgeAndInstruct(BaseModel):
    go_next: bool = Field(description="もし「次に進んで良い」と判定するのなら 'go_next'をtrueに，もし「とどまって，指示に従え」と判定するなら'go_next'をfalseに。")
    instruct: list[str] = Field(description="指示内容。1〜3の要素を持つ配列。", max_items=3, min_items=1)
    model_config = {
        "description": "userからの入力に対して、'go_next'と'instruct'を返す。",
    }



'''プログラム制御変数
'''
bSTREAM = True # Output by streaming
bDEBUG = False # Output debug information
thSummary = 8 # When len(chatlog) is over this number, cut the former num of thSummary elements

class InterviewerEngine:

    def __init__(self):
        '''状態変数
        '''
        self.count = 0 # 通算のターン数
        self.major_q_count = 0 # 主要質疑応答のターンの数
        self.minor_q_count = 0 # 追加の質疑応答のターン数
        self.chatlog_full = []  # チャットログ（全履歴）
        self.chatlog = []  # チャットログ（直近4ターン分のみ）
        self.chatlog4reporter = []  # シミュレーション用のAIReporterに投げるためのチャットログ
        self.summary = ""  # シンプル要約を格納・蓄積する変数
        self.current_chat = [] # 現在の主要質疑応答．Supervisorに渡す
        self.sub_chats = []  # 現在の追加質疑応答．Supervisorに渡す
        self.instructions = []# Supervisorからの指示を格納する変数
        self.past_instructions = []  # 過去に与えられた指示を格納する変数
        self.directions = [] # 指示全体を格納する変数．順にここからポップしていく
        self.direction = ""  # 現在の指示内容を格納する変数
        self.output_file = f"Study_Output/StudyV7_{time.strftime('%Y%m%d_%H%M%S')}.txt"  # Output file name

        """インタビューガイドの読み込み
        """
        for step in INTERVIEW_GUIDE["Steps"]:
            if "directions" in step:
                i = 0
                for direction in step["directions"]:
                    dir= {
                        "step": step["step"],
                        "title": step["title"],
                        "description": step["description"],
                        "No.": i,
                        "direction": direction
                    }
                    self.directions.append(dir)
                    i += 1
            if "substeps" in step:
                i = 0
                for substep in step["substeps"]:
                    i = 0
                    for direction in substep["directions"]:
                        dir = {
                            "step": step["step"],
                            "title": step["title"],
                            "substep": substep["substep"],
                            "subtitle": substep["title"],
                            # "subdescription": substep["description"],
                            "No.": i,
                            "direction": direction
                        }
                        self.directions.append(dir)
                        i += 1



    def write_output(self, output):
        """    Write output to a file.
        """
        with open(f"{self.output_file}", "a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y/%m/%d %H:%M:%S]") + "\n")
            f.write(output)


    def generate_question(self, direction="", instruction=""):
        """   質問を生成する関数
        """
        print("AI INTERVIEWER: ")
        if direction:
            message = f"[DIRECTION]\n{direction}"
        elif instruction:
            message = f"[INSTRUCTION]\n{instruction}"
        else:
            #エラーを投げる
            raise ValueError("Direction or instruction must be provided.")
       
        Question = Agent_chat(# Generate question
            messages=[{"role":"user", "content":f"[SUMMARY]\n{self.summary}"}] +\
                self.chatlog +\
                [{"role": "user", "content": message}],
            system_prompt=INTERVIEWER_J,
            temperature=0.0,
            stream=bSTREAM,
            Debug=bDEBUG
        ) 
        
        # if "\s*\[[a-zA-Z0-9_-\s]+\]" like "[summary]" or "[quesion]" is in Quesion, remove it. 
        # Those tags may be included in the response because input sentences have such a tag like "[Major Question]".
        Question = re.sub(r"\s*\[[^\]]*\]\s*", " ", Question)
        
        #ファイル保存
        output = f""" ******** turn {self.count} Major Question ********\nAI INTERVIEWER: {Question}\n"""; self.write_output(output)  # Write output to file

        return Question




    def first_question(self):
        """最初の質問はループの外．
        """
        self.direction = self.directions.pop(0)  # Get the first direction
        output = f"##################################\nStep {self.direction['step']}: {self.direction['title']}\n"
        output += f"Substep {self.direction['substep']}: {self.direction['subtitle']}\n" if "substep" in self.direction else "" 
        output += f"Direction: {self.direction['direction']}\n"
        print(output); self.write_output(output)  # Write output to file
        #endregion

        '''インタビュワーによる質問生成
        '''
        #region
        self.count += 1; 
        self.major_q_count += 1
        print(f"""*********** turn {self.count} **********\n""")
        Question = self.generate_question(direction=self.direction['direction'])
        return Question


    def generate_report(self, Question):
        """報告を生成する関数
        """
        print("AI Reporter: ")
        Report = Agent_chat( # Generate report
            messages=[{"role": "user", "content": f"[summary]\n{self.summary}"}] + self.chatlog4reporter + [{"role": "user", "content": Question}],
            system_prompt=REPORTER_J + f"\n\n[Scenario]: {json.dumps(SCENARIO_J, ensure_ascii=False)}",
            stream=bSTREAM,
            Debug=bDEBUG
        )
        output = f"AI REPORTER: {Report}\n"; self.write_output(output)  # Write output to file
        self.chatlog4reporter += [
            {"role": "user", "content": Question},
            {"role": "assistant", "content": Report}
        ]
        return Report


    def run(self, Report, Question):
        """報告から次の質問を生成するまでの一連の流れ
        ---
        Args:
            Report: 生成された報告
            Question: 生成された質問

        Returns:
            Question: 次の質問
            has_next: 次の質問があるかどうか（bool）
        """
        '''1. シンプル要約の生成
        '''
        print(f"AI SUMMARIZER: [turn {self.count}]")
        smry = Agent_chat(
            system_prompt="あなたは優秀な要約者です．与えられたQuestionとReportから，何が明らかになったのかを1文にまとめて出力してください．",
            messages=[
                {"role": "user", "content": f"[Question]\n{Question}"},
                {"role": "user", "content": f"[Report]\n{Report}"}
            ],
            temperature=0.0,
            stream=bSTREAM,
            Debug=bDEBUG
        )
        self.summary += smry


        '''2. チャットログへの追記
        '''
        if self.instructions:
            sub_chat = [
                {"role": "user", "content": f"[Minor Question {self.minor_q_count}]\n" + Question},
                {"role": "assistant", "content": f"[Minor Report {self.minor_q_count}]\n" + Report}
            ]
            self.sub_chats += sub_chat
            self.chatlog += sub_chat
            self.chatlog_full += sub_chat
        else:
            self.current_chat = [
                {"role": "assistant","content": f"[Major Question {self.major_q_count}]\n" + Question},
                {"role": "user", "content": f"[Major Report {self.major_q_count}]\n" + Report},
            ]
            self.chatlog += self.current_chat
            self.chatlog_full += self.current_chat
            self.sub_chats = []  # Reset sub_chats for the next instruction
            #endregion

    
        '''3. チャットログの整理
        チャットログのサイズがthSummaryを超えたら古いものは削除する．
        '''
        if len(self.chatlog) > thSummary:
            del self.chatlog[:len(self.chatlog)-thSummary]  # Remove all the elements other than the last thSummary elements
            del self.chatlog4reporter[:len(self.chatlog4reporter)-thSummary]  # Remove all the elements other than the last thSummary elements in chatlog4reporter
            output = f"AI SUMMARY: {self.summary}\n"; print(output); self.write_output(output)
    #endregion



        #region
        if self.instructions:
            """4'. Supervisorの指示に基づく追加質問の実施
            """
            instruction = self.instructions.pop(0)  # Get the first instruction
            self.past_instructions.append(instruction)  # Add the instruction to past_instructions
            self.count += 1; # 通算質問カウントの更新
            self.minor_q_count += 1 # 追加質問カウントの更新
            print(f"""*********** turn {self.count} Minor question {self.major_q_count}-{self.minor_q_count} **********\n""")            # 質問の生成
            Question = self.generate_question(instruction=instruction)
            return Question, len(self.directions) > 0



        else:
            """4. Supervisorによるチェック．
            SupervisorがTrueを返したら次のステップへ進む．
            もしFalseを返したら，Supervisorの指示に基づく追加質問を実施する．
            ただし，先にうけたSupervisorからの指示を実施中は，Supervisorのチェックはスキップする．
            """
            print("AI Supervisor: ")
            result = Agent_chat_parsed(
                messages=[
                    {"role":"user", "content": f"[DIRECTION]\n{self.direction['direction']}"},
                    {"role":"user", "content": f"[CurrentChat]\n{self.current_chat}"},
                    {"role":"user", "content": f"[SUB_CHATS]\n{self.sub_chats}"},
                ],
                system_prompt=SUPERVISOR_J,
                format=JudgeAndInstruct.model_json_schema(),  # Use the JudgeAndInstruct model to format the response
                temperature=0.0,
                Debug=bDEBUG
            )
            output = f"""AI Supervisor: {result}\n"""; self.write_output(output)  # Write output to file


            if str(result["go_next"]).lower() == "true":  # If the result is clear, break the loop
                """4.1 もしSupervisorがTrueを返したら，次のステップの質問生成に進む
                """
                self.direction = self.directions.pop(0)  # Get the first direction
                output = f"##################################\nStep {self.direction['step']}: {self.direction['title']}\n"
                output += f"Substep {self.direction['substep']}: {self.direction['subtitle']}\n" if "substep" in self.direction else "" 
                output += f"Direction: {self.direction['direction']}\n"
                print(output); self.write_output(output)  # Write output to file

                self.count += 1 # 通算質問カウントの更新
                self.major_q_count += 1 # 追加質問カウントの更新
                print(f"""*********** turn {self.count} **** Major question {self.major_q_count} **********\n""")
                # 質問の生成
                Question = self.generate_question(direction=self.direction['direction'])
                # もし今ポップしたdirectionが最後の要素だったら，ループを抜ける
                return Question , len(self.directions) > 0

                # if len(self.directions) == 0:
                #     """
                #     最後の要素に到達した場合の処理
                #     """
                #     print("質問終了")


            else:
                """4.2 SupervisorがFalseを返したら，Supervisorの指示に基づく追加質問を実施する．
                """
                '''Similarity Checker
                Supervisorが吐き出したinstructが，過去のinstructと意味的に同一かどうかを確認し，同一性が高いときには，その質問はパージする．
                '''
                for instruction_item in result["instruct"]:
                    is_Similar = False
                    for past_instruction_item in self.past_instructions:
                        res = Agent_chat_parsed(
                            messages=[
                                {"role": "user", "content": f"[1]\n{instruction_item}\n[2]{past_instruction_item}"}
                            ],
                            system_prompt="あなたは与えられた2つの文章が同じ意味を持つかどうかを判断するエキスパートです．\n[1]と[2]の文章が同じ意味を持つ場合は'true'，そうでない場合は'false'と答えてください．",
                            temperature=0.0,
                            format=CheckSimilarity.model_json_schema(),  # Use the CheckSimilarity model to format the response
                            Debug=bDEBUG
                        )
                        if str(res["is_similar"]).lower() == "true":
                            print(f"Skipping instruction: {instruction_item} (similar to past instruction: {past_instruction_item})")
                            is_Similar = True
                            break
                    if is_Similar:
                        continue
                    else: # If not similar, add to instructions
                        self.instructions.append(instruction_item)


                if not self.instructions:  # If there are no instructions left, break the loop
                    """
                    Supervisorの指示が空になった場合の処理
                    """
                    print("No new instructions found. Moving to the next step forcefully.")

                    direction = self.directions.pop(0)  # Get the first direction
                    output = f"##################################\nStep {direction['step']}: {direction['title']}\n"
                    output += f"Substep {direction['substep']}: {direction['subtitle']}\n" if "substep" in direction else "" 
                    output += f"Direction: {direction['direction']}\n"

                    self.count += 1 # 通算質問カウントの更新
                    self.major_q_count += 1 # 追加質問カウントの更新
                    print(f"""*********** turn {self.count} **** Major question {self.major_q_count} **********\n""")
                    # 質問の生成
                    Question = self.generate_question(direction=direction['direction'])
                    return Question, len(self.directions) > 0


                else:
                    '''Supervisorの指示に基づく追加質問の実施
                    '''
                    instruction = self.instructions.pop(0)  # Get the first instruction
                    self.past_instructions.append(instruction)  # Add the instruction to past_instructions
                    self.count += 1; # 通算質問カウントの更新
                    self.minor_q_count += 1 # 追加質問カウントの更新
                    print(f"""*********** turn {self.count} Minor question {self.major_q_count}-{self.minor_q_count} **********\n""")            # 質問の生成
                    Question = self.generate_question(instruction=instruction)
                    return Question, len(self.directions) > 0




    def generate_final_summary(self):
        """最終要約を生成する関数
        """
        summary_json = Agent_chat_parsed( # Generate summary
            messages=[{"role": "user", "content": self.summary}],
            system_prompt="あなたは与えられた文章をJSON形式に再構成するエキスパートです．与えられた文章を再構成してください．",
            max_tokens=8192,
            format= format_Report,
        )

        output = f"AI SUMMARY:\n{json.dumps(summary_json, ensure_ascii=False, indent=2)}\n"; print(output); self.write_output(output)  # Write output to file
        return summary_json


if __name__ == "__main__":

    engine = InterviewerEngine()

    Question = engine.first_question()  # 最初の質問を生成

    has_next = True
    while has_next:
        report = engine.generate_report(Question)
        Question, has_next = engine.run(report, Question)

    final_summary = engine.generate_final_summary()

    print(f"Final Summary:\n{json.dumps(final_summary, ensure_ascii=False, indent=2)}")

    