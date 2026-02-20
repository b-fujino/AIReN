import json
import time
import re
from pprint import pprint # 辞書形式のものを整えて出力する．


from systemprompt_Agent import INTERVIEWER_J, SUPERVISOR_J #, ELABORATOR_J, SUMMARIZER_J, PROOFWRITER, CHECKER
from systemprompt_Reporter import SCENARIO_J_2 as SCENARIO_J, REPORTER_J
from systemprompt_InterviewGuide_V2 import INTERVIEW_GUIDE_J as INTERVIEW_GUIDE
#from systemprompt_IncidentReportGuide import format_Report_J as format_Report
from systemprompt_IncidentReportGuide_Pydantic import IncidentReport_J as format_Report


from call_openai_api_Ollama import Agent_chat, Agent_chat_parsed, Agent_chat_tools
#from call_openai_api_openai import Agent_chat, Agent_chat_parsed
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
bSTREAM = False # Output by streaming
bDEBUG = False # Output debug information
thSummary = 4 # When the number of turns is over this number, cut the former num of thSummary*2 elements
SegmentingChars="。．.:;？?！!\n"

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
        self.primary_summary = []  # 1次要約を格納・蓄積する変数
        self.secondary_summary = []  # 2次要約を格納・蓄積する変数
        self.current_chat = [] # 現在の主要質疑応答．Supervisorに渡す
        self.sub_chats = []  # 現在の追加質疑応答．Supervisorに渡す
        self.instructions = []# Supervisorからの指示を格納する変数
        self.past_instructions = []  # 過去に与えられた指示を格納する変数
        self.directions = [] # 指示全体を格納する変数．順にここからポップしていく
        self.direction = ""  # 現在の指示内容を格納する変数
        self.output_file = f"Study_Output/StudyV7_{time.strftime('%Y%m%d_%H%M%S')}.txt"  # Output file name
        self.prev_question = ""
        self.prev_report = ""

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


    def generate_question(self, direction="", instruction="", Stream=False):
        """   質問を生成する関数
        """
        if direction:
            message = f"[DIRECTION]\n{direction}"
        elif instruction:
            message = f"[INSTRUCTION]\n{instruction}"
        else:
            #エラーを投げる
            raise ValueError("Direction or instruction must be provided.")

        #要約の準備
        if self.count <= thSummary:# 仮にthSummary=4とした場合，最初の4ターンは要約を使わない000
            summary = ""
        elif self.count <= thSummary*2: # 5〜8ターン目までは，直近4ターン分はそのままの会話ログをつかい、それ以前のターン分は１次要約を使う
            # summary = "\n".join(self.primary_summary[:-thSummary])  # Use the last thSummary elements for context
            summary = "\n".join([f"[{i}] {s}" for i, s in enumerate(self.primary_summary[:-thSummary])])  # インデックス付きでjoin

        else: # 9ターン目以降は，直近4ターン分はそのままの会話ログをつかい、それ以前の4ターン分は１次要約を使う、さらにそれ以前のターン分は２次要約を使う
            # summary = "\n".join(self.secondary_summary[:-2])  # Use the last thSummary elements for context
            summary = "\n".join([f"[{i}] {s}" for i, s in enumerate(self.secondary_summary[:-2])])  # インデックス付きでjoin
            # summary+= "\n".join(self.primary_summary[-thSummary*2:-thSummary])  # Use the last thSummary elements for context
            summary+= "\n".join([f"[{i}] {s}" for i, s in enumerate(self.primary_summary[-thSummary*2:-thSummary])])  # インデックス付きでjoin

        Question = Agent_chat(# Generate question
            messages=[{"role":"user", "content":f"[SUMMARY]\n{summary}"}] +\
                self.chatlog +\
                [{"role": "user", "content": message}],
            system_prompt=INTERVIEWER_J,
            temperature=0.0,
            stream=Stream,
            Debug=bDEBUG
        )

        if Stream==False: # Streamingでない場合
            # if "\s*\[[a-zA-Z0-9_-\s]+\]" like "[summary]" or "[quesion]" is in Quesion, remove it. 
            # Those tags may be included in the response because input sentences have such a tag like "[Major Question]".
            Question = re.sub(r"\s*\[[^\]]*\]\s*", " ", Question)
            
            #ファイル保存
            output = f""" ******** turn {self.count} Major Question ********\nAI INTERVIEWER: {Question}\n"""; self.write_output(output)  # Write output to file

            return Question

        def sentence_stream(): # Streamingの場合
            sentens = "" # 句を構成するためのバッファ　
            message = "" # プロンプトに含めるためにチャンクを結合させるためのためのバッファ            
            for chunk in Question:
                content = chunk
                if content:
                    message += content
                    # 1文字ずつ取り出してチェックする
                    for i in range(len(content)):
                        char = content[i]
                        sentens += char
                        if char in SegmentingChars: #今見ているのが区切り文字だった場合（読点も区切りに含める）
                            if i < len(content)-1: # i が最後の文字でないなら，次の文字をチェック
                                if content[i+1] not in SegmentingChars: #次の文字が区切り文字でないならyield
                                    sentens = re.sub(r"\s*\[[^\]]*\]\s*", " ", sentens) #もし"[summary]"や"[question]"のようなタグが含まれていたら削除
                                    yield sentens
                                    sentens = ""
                                else: #もし次の文字が区切り文字なら，現時点の区切り文字はスルー
                                    continue
                            else: #iが最後の文字の場合，現時点でyield
                                sentens = re.sub(r"\s*\[[^\]]*\]\s*", " ", sentens) #もし"[summary]"や"[question]"のようなタグが含まれていたら削除
                                yield sentens
                                sentens = ""
            if sentens: #最後にバッファに残っている文字があれば，それをyield
                yield sentens
                sentens = ""
            # 終了
            self.prev_question = message

            #ファイル保存
            output = f""" ******** turn {self.count} Major Question ********\nAI INTERVIEWER: {message}\n"""; self.write_output(output)  # Write output to file
        return sentence_stream()


    def sentence_stream(self, Question):
        """質問をチャンクに分割してyieldする関数
        """
        self.prev_question=""
        for seg in Question:
            yield seg
            self.prev_question += seg # チャンクを結合してself.prev_questionに格納

    def first_question(self, Stream=False):
        """最初の質問はループの外．
        """
        self.direction = self.directions.pop(0)  # Get the first direction

        #ファイル保存
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

        #ファイル保存
        output = f"""*********** turn {self.count} **********\n"""
        print(output); self.write_output(output)

        # 質問の生成
        Question = self.generate_question(direction=self.direction['direction'], Stream=Stream)
        if Stream==False:
            self.prev_question = Question       
            return Question
        else:
            return self.sentence_stream(Question)


    def generate_report(self, question=None, Stream=False):
        """報告を生成する関数
        """
        if question is None:
            Question = self.prev_question
        else:
            Question = question

        #要約の準備
        if self.count <= thSummary:
            summary = ""
        elif self.count <= thSummary*2:
            summary = "\n".join(self.primary_summary[:-thSummary])  # Use the last thSummary elements for context
        else:
            summary = "\n".join(self.secondary_summary[:-2])  # Use the last thSummary elements for context
            summary+= "\n".join(self.primary_summary[-thSummary*2:-thSummary])  # Use the last thSummary elements for context

        Report = Agent_chat( # Generate report
            messages=[{"role": "user", "content": f"[summary]\n{summary}"}] + self.chatlog4reporter + [{"role": "user", "content": Question}],
            system_prompt=REPORTER_J + f"\n\n[Scenario]: {json.dumps(SCENARIO_J, ensure_ascii=False)}",
            stream=Stream,
            Debug=bDEBUG
        )
        if Stream == False: # Streamingでない場合
            output = f"AI REPORTER: {Report}\n"; self.write_output(output)  # Write output to file
            self.chatlog4reporter += [
                {"role": "user", "content": Question},
                {"role": "assistant", "content": Report}
            ]
            self.prev_report = Report
            return Report
        # Streamingの場合
        def sentence_stream(): # Streamingの場合
            message = "" # プロンプトに含めるためにチャンクを結合させるためのためのバッファ
            sentens = "" # 句を構成するためのバッファ
            for chunk in Report:
                content = chunk
                if content:
                    message += content
                    # 1文字ずつ取り出してチェックする
                    for i in range(len(content)):
                        char = content[i]
                        sentens += char
                        if char in SegmentingChars: #今見ているのが区切り文字だった場合（読点も区切りに含める）
                            if i < len(content)-1: # i が最後の文字でないなら，次の文字をチェック
                                if content[i+1] not in SegmentingChars: #次の文字が区切り文字でないならyield
                                    yield sentens
                                    sentens = ""
                                else: #もし次の文字が区切り文字なら，現時点の区切り文字はスルー
                                    continue
                            else: #iが最後の文字の場合，現時点でyield
                                yield sentens
                                sentens = ""

            output = f"AI REPORTER: {message}\n"; self.write_output(output)  # Write output to file
            self.chatlog4reporter += [
                {"role": "user", "content": Question},
                {"role": "assistant", "content": message}
            ]
            self.prev_report = message

        return sentence_stream()


    def _Summarize(self, Question, Report):
        """要約を更新する関数
        """
        '''1. １次要約の生成
        各ターンごとに，QuestionとReportを要約化してself.primary_summaryに格納する
        '''
        print(f"AI SUMMARIZER: [turn {self.count}]")
        smry = Agent_chat(
            system_prompt="あなたは優秀な要約者です．与えられたQuestionとReportから，何が明らかになったのかを1文にまとめて出力してください．",
            messages=[
                {"role": "user", "content": f"[Question]\n{Question}"},
                {"role": "user", "content": f"[Report]\n{Report}"}
            ],
            temperature=0.0,
            stream=False,
            Debug=bDEBUG
        )
        print(smry)
        self.primary_summary.append(smry)

        '''2. ２次要約の生成
        turnがthSummary回ごとに，古いものをまとめて要約化する
        '''
        if self.count % thSummary == 0:
            print("AI SUMMARIZER: Summarizing the summary...")
            smry2 = Agent_chat(
                system_prompt="あなたは優秀な要約者です．与えられた文章を要約してください．",
                messages=[
                    {"role": "user", "content": f"[Summary]\n" + "\n".join(self.primary_summary[-thSummary:])}
                ],
                temperature=0.0,
                stream=False,
                Debug=bDEBUG
            )
            print(smry2)
            self.secondary_summary.append(smry2) # 古いsummaryをまとめて要約化したものだけに置き換える



    def run(self, Question=None, Report=None, Stream=False):
        """報告から次の質問を生成するまでの一連の流れ
        ---
        Args:
            Report: 生成された報告

        Returns:
            Question: 次の質問（returnすると同時にself.prev_questionに格納）
            has_next: 次の質問があるかどうか（bool）
        """
        if Report is None:
            Report = self.prev_report
        if Question is None:    
            Question = self.prev_question

        '''1. 要約の更新
        '''
        self._Summarize(Question, Report) # 要約の更新



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
        if len(self.chatlog) > thSummary*2:  # If chatlog exceeds twice the threshold, summarize and trim
            del self.chatlog[:len(self.chatlog)-thSummary]  # Remove all the elements other than the last thSummary elements
            del self.chatlog4reporter[:len(self.chatlog4reporter)-thSummary]  # Remove all the elements other than the last thSummary elements in chatlog4reporter
            output = f"AI SUMMARY: {self.primary_summary}\n"; print(output); self.write_output(output)
            output = f"AI SUMMARY2: {self.secondary_summary}\n"; print(output); self.write_output(output)
    #endregion



        #region
        if self.instructions:
            """4'. Supervisorの指示に基づく追加質問の実施
                もしself.instructionsが空でなかったら，Supervisorの指示に基づく追加質問を実施する．
            """
            instruction = self.instructions.pop(0)  # Get the first instruction
            self.past_instructions.append(instruction)  # Add the instruction to past_instructions
            self.count += 1; # 通算質問カウントの更新
            self.minor_q_count += 1 # 追加質問カウントの更新
            print(f"""*********** turn {self.count} Minor question {self.major_q_count}-{self.minor_q_count} **********\n""")            # 質問の生成
            Question = self.generate_question(instruction=instruction, Stream=Stream)
            if Stream==False:
                self.prev_question = Question
                return Question, len(self.directions) > 0
            else:

                return self.sentence_stream(Question), len(self.directions) > 0



        else:
            """4. Supervisorによるチェック．
                SupervisorがTrueを返したら次のステップへ進む．
                もしFalseを返したら，Supervisorの指示に基づく追加質問を実施する．
                ただし，先にうけたSupervisorからの指示を実施中は，Supervisorのチェックはスキップする．
            """
            result = Agent_chat_parsed(
                messages=[
                    {"role":"user", "content": f"[DIRECTION]\n{self.direction['direction']}"},
                    {"role":"user", "content": f"[CurrentChat]\n{self.current_chat}"},
                    {"role":"user", "content": f"[SUB_CHATS]\n{self.sub_chats}"},
                ],
                system_prompt=SUPERVISOR_J,
                format=JudgeAndInstruct,  # Use the JudgeAndInstruct model to format the response
                temperature=0.0,
                Debug=bDEBUG
            )

            print("AI Supervisor: ")
            pprint(result)
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
                Question = self.generate_question(direction=self.direction['direction'], Stream=Stream)

                # もし今ポップしたdirectionが最後の要素だったら，ループを抜ける
                if Stream==False:
                    self.prev_question = Question       
                    return Question, len(self.directions) > 0
                else:

                    return self.sentence_stream(Question), len(self.directions) > 0


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
                            format=CheckSimilarity,  # Use the CheckSimilarity model to format the response
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
                    Question = self.generate_question(direction=direction['direction'], Stream=Stream)
                    # 質問の生成 streamingでない場合
                    if Stream == False:
                        self.prev_question = Question
                        return Question, len(self.directions) > 0
                    
                    # Streamingの場合
                    else:
                        return self.sentence_stream(Question), len(self.directions) > 0

                else:
                    '''Supervisorの指示に基づく追加質問の実施
                    '''
                    instruction = self.instructions.pop(0)  # Get the first instruction
                    self.past_instructions.append(instruction)  # Add the instruction to past_instructions
                    self.count += 1; # 通算質問カウントの更新
                    self.minor_q_count += 1 # 追加質問カウントの更新
                    print(f"""*********** turn {self.count} Minor question {self.major_q_count}-{self.minor_q_count} **********\n""")            # 質問の生成
                    Question = self.generate_question(instruction=instruction, Stream=Stream)
                    if Stream==False:
                        self.prev_question = Question       
                        return Question, len(self.directions) > 0
                    else:
                        return self.sentence_stream(Question), len(self.directions) > 0
        #endregion




    def generate_final_summary(self):
        """最終要約を生成する関数
        """
        #二次サマリーを文字列にまとめる
        summary_text = "[SECONDARY SUMMARY]\n" + "\n".join(self.secondary_summary)

        #一次サマリーのうち、二次サマリーに含まれていないものを文字列にまとめる
        tail = self.count % thSummary
        if tail:
            summary_text += "\n\n[PRIMARY SUMMARY TAIL]\n" + "\n".join(self.primary_summary[-tail:])
        
        summary_json = Agent_chat_parsed( # Generate summary
            messages=[{"role": "user", "content": summary_text}],
            system_prompt="あなたは与えられた文章をJSON形式に再構成するエキスパートです．与えられた文章を再構成してください．",
            max_tokens=8192,
            format= format_Report,
        )

        output = f"AI SUMMARY:\n{json.dumps(summary_json, ensure_ascii=False, indent=2)}\n"; print(output); self.write_output(output)  # Write output to file
        return summary_json
    
    def json_to_md(data, level=1, parent_key=None):
        """Convert JSON data to Markdown format."""
        md = ""
        heading = "#" * level
        if parent_key:
            md += f"{heading} {parent_key}\n\n"
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, dict):
                    md += json_to_md(val, level + 1, key)
                elif isinstance(val, list):
                    md += f"{'#' * (level + 1)} {key}\n"
                    for item in val:
                        if isinstance(item, (dict, list)):
                            md += json_to_md(item, level + 2)
                        else:
                            md += f"- {item}\n"
                    md += "\n"
                else:
                    md += f"- **{key}**: {val}\n"
            md += "\n"
        else:
            md += f"- {data}\n"
        return md


if __name__ == "__main__":

    engine = InterviewerEngine()

    __DEBUG__ = True
    
    if __DEBUG__ is not True:
        print("AI Interviewer: ")
        Question = engine.first_question(bSTREAM)  # 最初の質問を生成
        for seg in Question:
            print(seg, end="", flush=True)
        print()  # 改行

        has_next = True
        while has_next:
            report = engine.generate_report(Stream=bSTREAM)
            print("AI Reporter: ")
            if bSTREAM==False:
                print(report)  # 改行
            else:
                for sent in report:
                    print(sent, end="", flush=True)
                print()  # 改行

            Question, has_next = engine.run(Stream=bSTREAM)  # 次の質問を生成
            print("AI INTERVIEWER: ")
            if bSTREAM==False:
                print(Question)  # 改行
            else:
                for sent in Question:
                    print(sent, end="", flush=True)
                print()  # 改行

        final_summary = engine.generate_final_summary()
    
    if __DEBUG__ is True:
        engine.secondary_summary=['電気工事士の福井健太氏（35歳、8年勤務）は、工場内の分電盤前での配線作業中にニアミスが発生した。', '福井さんのニアミスは、2023年7月15日の午前10時頃に工場内の分電盤前で発生したことが明らかになった。\n', '配線作業中に電源が切れていると誤認しゴム手袋を外してケーブルに触ろうとしたところ、一部回路の電源が入っており、指先に感電するニアミスが発生した。', '福井さんは、上司からの指示と前工程の確認が済んでいるという認識に基づいて再確認を省略して作業を進めていたため、電源が切られているにも関わらず感電の危険に遭遇した。', '福井さんは、工期がタイトな状況下で確認を省略してしまったものの、事象発生直前に体調に変化はなかったと報告している。', '福井さんは、指示通りに作業を進めていたものの、急いでいたため少し焦っていたが、電源が切れていることを認識していたため特に不安はなかったと報告した。', '福井さんは、過去の経験と上司からの指示に基づき、今回の作業で電源が遮断されていると強く確信していた。\n', '分電盤の周辺には、作業中のケーブル、以前から繋がっていたケーブル、工具箱、点灯していない懐中電灯が存在していた。', '福井さんは、事象発生時に電源遮断の確認方法（分電盤表示と電圧計での電圧確認）や作業前の確認事項（周囲の安全確認と工具の確認）が作業手順書に記載されていたことを証言しました。\n', '福井さんは作業中に、特別な指示、アラーム、サイン、通知など、変わった情報や異変は一切なかったと報告した。\n', '福井さんは、事象発生時の作業場の温度が25度、湿度がやや高め、騒音レベルは通常通り、明るさは十分であったと証言しました。', '福井さんによると、事象が発生した場所は横3メートル、奥行き2メートルの広さで、作業中は分電盤周りの配線ケーブルが足元に散らばっており、少し邪魔に感じていたとのことです。\n', '福井さんは、事象発生場所に普段と変わった人や物、動きなどを特に認識していなかった。\n', '福井さんは、事象発生場所の分電盤横の床に、いつもと違う小さな工具箱が置かれていたような気がすると証言したが、確信はないとのことである。\n', '福井さんの証言から、事象発生時に福井さんの近くにいたのは同僚の山田さんで、山田さんは福井さんの作業を観察していたものの、二人の間に具体的な会話はなかったことが明らかになった。', '福井さんは、朝礼で安全確認の指示を受け、作業手順書に従って分電盤の配線作業をしていたが、工期への焦りから安全確認を省略し、結果的に感電事故に遭遇した。', '福井さんは、山田さんが作業を見守っていたことに特別な意図を感じたわけではないものの、見られているという意識が集中力を少し妨げたと感じている。', '福井さんは、分電盤の配線作業前に、電源スイッチ、電圧テスター、遮断器、絶縁抵抗計を用いて、回路に電圧が印加されていないこと、遮断器がOFFの状態であること、配線経路に絶縁不良がないことを確認し、安全性を確保した。', '福井さんは、作業手順書に記載された電源遮断の確認方法を全て実行し、手順書との間に相違がないことを報告しました。', '福井さんは、電圧テスターで各回路の電圧が0.00Vであり、絶縁抵抗計で配線経路の絶縁抵抗が10MΩ以上であることを確認し、手順書に記載された内容と実際に実行された内容に相違がないことを証明した。', '福井さんは、普段から電気工事の作業でリスクを意識し、作業手順の再確認、電源遮断確認、絶縁状態確認などを徹底しているが、今回の作業では上司の指示を鵜呑みにして自分で確認を怠ったため、ニアミスが発生したことを反省し、今後は自己確認を徹底するつもりである。', '福井さんは、上司からの「全て遮断済み」という指示のもと、手順書を確認し、通常と変わらない状況で作業を進めていたものの、感電した際に自身の認識が間違っていたことに気づいた。', '福井さんは、感電事故発生前に上司からリスクに関する具体的な指示や注意喚起は一切なく、工期を急ぐ旨の指示のみを受けていたことが明らかになった。', '福井さんは、今回のニアミスを避けるためには、作業前の電源遮断の再確認、作業手順書の再確認、周囲の状況確認、上司への確認、作業中の集中力維持と確認の徹底、そして上司からの遮断確認方法や遮断範囲の明確化、リスク情報提供、進捗確認が重要だと考えている。', '福井さんは今回のニアミスを経験したことで、上司の指示だけでなく自身の判断と確認の重要性を痛感し、今後はより主体的に安全性を確認し、不安を感じたら積極的に相談することで、責任感を持って仕事に取り組むことを決意した。', '福井さんは、工期、品質、コストのプレッシャーを抱えながらも、作業計画の徹底、手順の遵守、効率化などを通じて対応しており、今回のニアミスを教訓に、今後は安全性を最優先に冷静に判断していく決意を表明した。', '福井さんは、電気工事士としての仕事に高いモチベーションを感じており、達成感、貢献感、技術の向上、そして顧客からの感謝がその源泉であり、今回のニアミスを教訓に、安全性を最優先に質の高い仕事を提供し続けたいと考えていることが明らかになった。', '福井さんは、電気工事の仕事において、問題解決、創造性、チームワーク、スキルアップといった多岐にわたる要素に満足しており、それらが仕事のやりがいとモチベーションの源泉となっている。', '福井さんは、普段の業務プロセスやスケジュール、体力的な負担にはある程度の定常性があるものの、工期へのプレッシャーからスケジュール管理の徹底と体力的な負担の考慮が課題であると認識している。', '福井さんは、現場の照明、温度・湿度、騒音、作業スペース、設備のメンテナンス状況に改善の必要性を感じており、それらの改善が作業効率と安全性の向上に繋がると考えている。', '福井さんは、新しい技術や安全、工期、予算に関する情報提供の頻度や形に改善の余地を感じており、情報伝達のスムーズ化がより効率的で安全な作業に繋がると考えている。', '福井さんは、同僚との良好な連携を築きつつも、上司からの指示の曖昧さやプレッシャー、部署間のコミュニケーション不足といった課題を感じており、改善の余地があると考えている。', '福井さんは、職場全体の雰囲気を概ね活気があり協力的だと感じているものの、部署間の連携不足、上層部からの指示の不明確さ、長時間労働といった課題も認識しており、これらの改善によって更なるモチベーション向上を目指している。', '福井さんは、現在のトレーニング、リスク管理、業務プロセス、部署運営方針に課題を感じており、現場の状況に合わせた改善や、部門間の連携強化などを通じて、より効率的で安全な職場環境の構築を目指している。', '福井さんは、組織全体の意思決定プロセス、情報開示、レベル間のコミュニケーション、経営理念の浸透において、現場の意見反映不足、情報共有の不十分さ、一方的なコミュニケーション、形式的な理解といった課題を指摘し、改善の必要性を訴えている。', '福井さんは、電気工事士としての仕事にやりがいを感じ、会社への貢献意欲はあるものの、組織の運営方針や情報開示の改善を期待しており、それらが満たされればより積極的に貢献したいと考えている。', '福井さんは、ヒヤリハットやインシデントの発現には、情報伝達の不備、リスクアセスメントの不十分さ、作業手順書の不備、工期へのプレッシャーなど、組織、プロセス、個人、その他の様々な要因が複合的に関与していると考えている。', '福井さんのヒヤリハット・インシデント要因分析は、組織的・プロセス的要因が根本原因となることが多いという点に同意し、変化への対応の遅れとコミュニケーションスタイルの問題の追加提案を含め、今後のリスク管理や安全対策に重要な示唆を与えている。']
        final_summary = engine.generate_final_summary()

    print(f"Final Summary:\n{json.dumps(final_summary, ensure_ascii=False, indent=2)}")

    