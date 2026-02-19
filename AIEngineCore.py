import json
import time
import re
from pprint import pprint # 辞書形式のものを整えて出力する．


from systemprompt_Agent import INTERVIEWER_J, SUPERVISOR_J #, ELABORATOR_J, SUMMARIZER_J, PROOFWRITER, CHECKER
from systemprompt_Reporter import SCENARIO_J_2 as SCENARIO_J, REPORTER_J
from systemprompt_InterviewGuide_V2 import INTERVIEW_GUIDE_J as INTERVIEW_GUIDE
from systemprompt_IncidentReportGuide import format_Report_J as format_Report

#from call_openai_api_Ollama import Agent_chat, Agent_chat_parsed, Agent_chat_tools
from call_openai_api_openai import Agent_chat, Agent_chat_parsed
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

    print(f"Final Summary:\n{json.dumps(final_summary, ensure_ascii=False, indent=2)}")

    