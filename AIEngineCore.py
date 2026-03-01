import json
import time
import re
from pprint import pprint # 辞書形式のものを整えて出力する．


from systemprompt_Agent_V2 import INTERVIEWER_J, SUPERVISOR_J, Summarizer_Primary, Summarizer_Secondary, SimilarityChecker_J #, ELABORATOR_J, SUMMARIZER_J, PROOFWRITER, CHECKER
from systemprompt_Reporter import REPORTER_J, SCENARIO_J_1, SCENARIO_J_2 , SCENARIO_J_3, SCENARIO_J_4, SCENARIO_J_5
from systemprompt_InterviewGuide_V2 import INTERVIEW_GUIDE_J as INTERVIEW_GUIDE
#from systemprompt_IncidentReportGuide import format_Report_J as format_Report
from systemprompt_IncidentReportGuide_Pydantic import IncidentReport_J as format_Report


from call_openai_api_Ollama import Agent_chat, Agent_chat_parsed, Agent_chat_tools
#from call_openai_api_openai import Agent_chat, Agent_chat_parsed
#from call_openai_api import Agent_chat, Agent_chat_parsed, Agent_chat_tools
#from call_openai_api_Groq import Agent_chat, Agent_chat_parsed, Agent_chat_tools


'''
構造化出力のためのPydanticモデル
'''
from pydantic import BaseModel, Field

class CheckSimilarity(BaseModel):
    is_similar: bool = Field(description="もし意味が同じなら, true; もし意味が違っていたら, false.")

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

    '''
     その他の関数   
     '''

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
        if self.count < thSummary:# 仮にthSummary=4とした場合，最初の4ターンは要約を使わない000
            summary = ""
        elif self.count < thSummary*2: # 5〜8ターン目までは，直近4ターン分はそのままの会話ログをつかい、それ以前のターン分は１次要約を使う
            # summary = "\n".join(self.primary_summary[:-thSummary])  # Use the last thSummary elements for context
            summary = "\n".join([f"[{i}] {s}" for i, s in enumerate(self.primary_summary[:-thSummary])])  # インデックス付きでjoin

        else: # 9ターン目以降は，直近4ターン分はそのままの会話ログをつかい、それ以前の4ターン~8ターン分は１次要約を使う、さらにそれ以前のターン分は２次要約を使う
            # summary = "\n".join(self.secondary_summary[:-2])  # Use the last thSummary elements for context
            summary = "\n".join([f"[{i}] {s}" for i, s in enumerate(self.secondary_summary[:-2])])  # インデックス付きでjoin
            # summary+= "\n".join(self.primary_summary[-thSummary*2:-thSummary])  # Use the last thSummary elements for context
            summary+= "\n".join([f"[{i}] {s}" for i, s in enumerate(self.primary_summary[-(thSummary*2+self.count%thSummary):-thSummary])])  # インデックス付きでjoin

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
        """最初の質問wを生成する関数
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

        # #要約の準備
        # if self.count < thSummary:
        #     summary = ""
        # elif self.count < thSummary*2:
        #     summary = "\n".join(self.primary_summary[:-thSummary])  # Use the last thSummary elements for context
        # else:
        #     summary = "\n".join(self.secondary_summary[:-2])  # Use the last thSummary elements for context
        #     summary+= "\n".join(self.primary_summary[-thSummary*2:-thSummary])  # Use the last thSummary elements for context

        #要約の準備
        if self.count < thSummary:# 仮にthSummary=4とした場合，最初の4ターンは要約を使わない000
            summary = ""
        elif self.count < thSummary*3: # 5〜11ターン目までは，直近4ターン分はそのままの会話ログをつかい、それ以前のターン分は１次要約を使う
            # summary = "\n".join(self.primary_summary[:-thSummary])  # Use the last thSummary elements for context
            summary = "\n[Primary Summary]".join([f"[P{i}] {s}" for i, s in enumerate(self.primary_summary[:-thSummary])])  # インデックス付きでjoin

        else: # 11ターン目以降は，直近4ターン分はそのままの会話ログをつかい、直近5ターン目から8+count%thSummary目までは１次要約を使う、さらにそれ以前のターン分は２次要約を使う
            # summary = "\n".join(self.secondary_summary[:-2])  # Use the last thSummary elements for context
            summary = "\n[Secondary Summary]".join([f"[S{i}] {s}" for i, s in enumerate(self.secondary_summary[:-2])])  # インデックス付きでjoin
            # summary+= "\n".join(self.primary_summary[-thSummary*2:-thSummary])  # Use the last thSummary elements for context
            summary+= "\n\n[Primary Summary]".join([f"[P{i}] {s}" for i, s in enumerate(self.primary_summary[-(thSummary*2+self.count%thSummary):-thSummary])])  # インデックス付きでjoin



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
            system_prompt=Summarizer_Primary,
            messages=[
                {"role": "user", "content": f"[Question]\n{Question}\n\n [Report]\n{Report}\n"}
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
                system_prompt=Summarizer_Secondary, #"あなたは優秀な要約者です．与えられた文章を要約してください．",
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
        msgs_per_turn = 2                # Question + Report
        keep_turns = thSummary           # 例: 4ターン残したい
        keep_msgs = keep_turns * msgs_per_turn     # 8メッセージ残す
        trim_trigger = keep_msgs * 2               # 16メッセージ超えたら刈る
        if len(self.chatlog) > trim_trigger:  
            '''
            If chatlog exceeds forth the threshold, summarize and trim. 
            Note len(chatlog) counts the number of messages, not turns, 
            so it can be 2*thSummary when the number of turns is thSummary.
            So If the number of turns is over thSummary*2, the chatlog can exceed thSummary*2*2.
            '''
            del self.chatlog[:-keep_msgs]  # Remove all the elements other than the last thSummary elements
            del self.chatlog4reporter[:-keep_msgs]  # Remove all the elements other than the last thSummary elements in chatlog4reporter
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


            if result.go_next: #str(result["go_next"]).lower() == "true":  # If the result is clear, break the loop
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
                for instruction_item in result.instruct: #result["instruct"]:
                    is_Similar = False
                    for past_instruction_item in self.past_instructions:
                        res = Agent_chat_parsed(
                            messages=[
                                {"role": "user", "content": f"[1]\n{instruction_item}\n[2]{past_instruction_item}"}
                            ],
                            system_prompt=SimilarityChecker_J, #"あなたは与えられた2つの文章が同じ意味を持つかどうかを判断するエキスパートです．\n[1]と[2]の文章が同じ意味を持つ場合は'true'，そうでない場合は'false'と答えてください．",
                            temperature=0.0,
                            format=CheckSimilarity,  # Use the CheckSimilarity model to format the response
                            Debug=bDEBUG
                        )
                        if res.is_similar: #str(res["is_similar"]).lower() == "true":
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




    def generate_final_summary(self, flag_primary=True):
        """最終要約を生成する関数
           args:
                flag_primary: 
                    True (default): primary_summaryの内容をもとに最終要約を生成する．
                    False: secondary_summary+primary_summaryの末尾の内容をもとに最終要約を生成する． 
        """
        if flag_primary:
            summary_text = "[PRIMARY SUMMARY]\n" + "\n".join(self.primary_summary)  #一次サマリーを文字列にまとめる
        else:
            #二次サマリーを文字列にまとめる
            summary_text = "[SECONDARY SUMMARY]\n" + "\n".join(self.secondary_summary)

            #一次サマリーのうち、二次サマリーに含まれていないものを文字列にまとめる
            tail = self.count % thSummary
            if tail:
                summary_text += "\n\n[PRIMARY SUMMARY TAIL]\n" + "\n".join(self.primary_summary[-tail:])
        
        summary_json = Agent_chat_parsed( # Generate summary
            messages=[{"role": "user", "content": summary_text}],
            system_prompt="あなたは与えられた文章を指定された形式に再構成するエキスパートです．与えられた文章を再構成してください．",
            max_tokens=8192,
            format= format_Report,
        )
        
        print(summary_json)
        #output = f"AI SUMMARY:\n{json.dumps(summary_json, ensure_ascii=False, indent=2)}\n"; print(output); self.write_output(output)  # Write output to file
        print(summary_json.model_dump_json(indent=2, ensure_ascii=False))

        return summary_json.model_dump_json(indent=2, ensure_ascii=False)
    
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


def AIReNTest(bSTREAM=False, turn_num=0, idx=0):
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
    
    with open(f"Study_Output/SCENARIO_{idx}_Ollama_AIReN_turn_{turn_num}_{time.strftime('%Y%m%d_%H%M%S')}_debug.json", "w", encoding="utf-8") as f:
        json.dump(final_summary, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # for tn in range(0, 10):
    #     AIReNTest(bSTREAM=False, turn_num=tn)
    # global SCENARIO_J
    # for tn in range(0, 10):
    #     for idx, scenario in enumerate([ SCENARIO_J_1, SCENARIO_J_2 , SCENARIO_J_3, SCENARIO_J_4, SCENARIO_J_5], start=1):
    #         SCENARIO_J = scenario
    #         AIReNTest(bSTREAM=False, turn_num=tn, idx=idx)
    
    SCENARIO_J = SCENARIO_J_5
    idx = 5
    tn = 9
    AIReNTest(bSTREAM=False, turn_num=tn, idx=idx)

    # engine = InterviewerEngine()
    # engine.primary_summary = ['[PRIMARY SUMMARY]\n## Summary\n\nThe purpose of this interview, led by Risa Minase, is to understand the details of a recent near miss/incident to prevent recurrence.  The interviewer assures Sakura Ashiba that the interview is not for blame or criticism, but to facilitate organizational learning and improve work processes.  Information provided will be strictly confidential.\n\nSakura Ashiba, 32 years old, has worked as a clerical staff member at the company for 5 years. Her role in the near miss was operating the customer management system.\n\n足羽さんによる顧客管理システムのニアミスは、2023年12月5日の午後13時30分頃、足羽さんの自席で発生したことが判明しました。\n\n2023年12月5日午後13時30分頃、足羽さんの自席でニアミスが発生した。\n\n*   足羽さんは顧客管理システムで業務中に、上司からの急な来客対応で席を離れた。\n*   席を離れている間に、業務委託で訪れていた外部業者の男性がデスク付近を通った。\n*   外部業者は足羽さんのモニターが見える位置を通ったが、足羽さんの画面に注意を払っていなかったため、情報漏洩には至らなかった。\n*   席に戻った後、外部業者が近くにいたことに気づき、動揺した。\n足羽さんは、上司からの急な依頼で席を離れた際、特に確認することなく慌てて席を立った。その後、画面ロックをかけるべきだったと反省し、外部業者の存在に不安を感じたことが報告された。\n\n足羽さんは、席を離れる直前、体調に変化はなかったと述べています。昼休憩後で少し眠かったかもしれないとのことですが、普段と比べて特に疲労や痛み、不快感は感じていなかったようです。\n\n足羽さんは、ニアミスが発生する直前は**業務に集中していた**ものの、**上司からの急な依頼で少し慌てていた**と述べています。また、**昼休憩後で注意力が散漫になっていた可能性**も認識しているようです。冷静な判断については自信がないとのことです。\n\n**明らになったこと:**\n\n*   **判断力への自信の欠如:** 報告者は今回の件で自身の判断力に自信がないと認めている。\n*   **具体的な課題:**\n    *   席を離れる前の画面ロックの未実施\n    *   外部業者の存在への気づきと対応の遅れ\n*   **普段の行動との乖離:** 普段は顧客情報を取り扱う際に画面ロックを必ずかけるように心がけているが、今回はそれを怠ってしまった。\n*   **状況による判断力の低下:** 当日の状況により、普段の注意を払えなかったことが、判断力の甘さにつながったと認識している。\n足羽さんは、今回のニアミスについてご自身の判断力に不安を感じている。\n\nニアミス発生時に使用していた機器は以下の通り。\n\n*   **PC:** 自作デスクトップPC (OS: Windows 10)\n*   **顧客管理システム:** 社内開発のオリジナルシステム\n*   **モニター:** 27インチ液晶モニター\n*   **キーボード・マウス:** 一般的なもの\n\nこれらの機器は当時正常に動作しており、特に不具合はなかったと考えている。\n\n**明らになったこと:**\n\n*   顧客管理システムの操作マニュアルが存在する。\n*   マニュアルには、「顧客情報が表示されている画面では必ず画面ロックをかける」というルールが記載されている。\n*   外部業者への対応に関する具体的な指示はマニュアルには記載されていない。\n*   社内規定として、顧客情報に関わる業務を行う際は情報漏洩に注意することが定められている。\n\n**要約:**\n\n顧客管理システムの操作中に、画面ロックが発生した原因について、特別な情報（システムアラーム、画面上のサイン、上司からの指示）は一切なかったことが確認された。\n\n今回のニアミス発生時の作業場環境について、以下の点が明らかになりました。\n\n*   **室温:** エアコンで24度程度に調整されていた。\n*   **湿度:** 普段より少し高めだった可能性がある。\n*   **騒音レベル:** 普段と変わらず、キーボードの打鍵音や社内の話し声が聞こえていた。\n*   **明るさ:** 十分で、自然光とデスクライトの両方で明るかった。\n\n**明らになったこと:**\n\n*   足羽さんの作業スペースは、横120cm、奥80cmの広さである。\n*   作業スペースには、パソコン関連機器（パソコン本体、モニター、キーボード、マウス）とメモ帳、ペンが置かれていた。\n*   書類はほとんどなく、足羽さんは常に整理整頓を心がけている。\n\n**明らになったこと:**\n\n*   ニアミスが発生した際、足羽さんの作業スペースに、普段見かけない外部業者が現れていた。\n*   外部業者は足羽さんのデスクの少し手前に立っており、ニアミス直前にモニター画面を見ていた。\n\nつまり、ニアミス発生時に外部業者が足羽さんの作業に影響を与えていた可能性が示唆された。\n\n**明らかなこと:**\n\n*   質問者が、外来業者とのニアミスについて確認しており、その業者との普段の関係性や、ニアミス直前のやり取りについて尋ねている。\n*   回答者は、その外来業者との普段からのコミュニケーションは特にない。\n*   ニアミス直前に、業者と会話をしたり、指示を受けたりしたことはなかった。\n今回のニアミス発生日の状況は以下の通りです。\n\n*   **7時起床、8時45分出社:** 通常通りの朝、電車通勤で会社に到着。\n*   **顧客管理システムの作業:** 出勤後、顧客情報の入力作業を開始。\n*   **12時半頃昼休憩:** 社員食堂で昼食。\n*   **13時15分頃、上司からの急な依頼:** 〇〇の資料確認のため席を離れる。\n*   **席を離れる際のミス:** 顧客管理システムに表示されていた顧客情報に気づかず、画面ロックをかけ忘れる。\n*   **会議室での資料確認:** 上司の指示に従い資料を確認。\n*   **外部業者との遭遇:** 席に戻った後、外部業者がモニターの画面を見ているのを発見し、慌てて画面を閉じる。\n*   **反省:** 画面ロックをかけるべきだったと反省。\n\n要するに、**上司からの急な依頼で席を離れる際に、顧客管理システムの画面ロックをかけ忘れたことが、外部業者に顧客情報を見られるというニアミスにつながった**ことが明らかになりました。\n\n**明らになったこと:**\n\n*   朝食は食パンとコーヒーを少し食べた。\n*   家を出る前にニュースを少し見た。\n*   天気予報を確認したが、晴れだったので傘は持っていかなかった。\n*   朝はいつもと変わらない、特別な出来事はなかった。\n\n**明らになったこと:**\n\n*   天気予報を確認した際、特に心当たりや注意すべき点はありませんでした。\n*   普段から通勤時のニュースや天気予報をチェックしています。\n*   普段はリスク予測や注意はしていませんが、その日は午後の重要な顧客との打ち合わせのため、時間に余裕を持って行動しようとしていました。\n顧客との打ち合わせについて、以下の点が明らかになりました。\n\n*   **事前の準備:** 報告者は、顧客の要望と提案内容の確認、必要なデータの整理、想定される質問と回答の準備など、事前の準備を丁寧に行っていた。\n*   **時間的な余裕:** 打ち合わせまでに時間的な制約を感じることなく、余裕を持って準備できた。\n\n**明らになったこと:**\n\n*   今回のニアミス直前、顧客との打ち合わせに関して、**特別な情報や指示は特にありませんでした**。\n*   打ち合わせの**重要度は普段と変わらない**認識で臨まれました。\n*   **時間的な制約も特に指示されていませんでした**。\n*   顧客に関する**特別な注意点も伝えられていませんでした**。\n*   ただし、**「〇〇の件について、顧客に確認が必要になったら、すぐに連絡してほしい」**という上司からの指示はありました。\n## 要約\n\n**Question:** ニアミスを避けるために、上司がどのような状況を期待していたか？\n\n**Reportからの結論:**\n\n*   **特別な注意喚起はなかった:** 画面ロックや顧客管理システムの利用に関する新たな指示や注意喚起は行われていない。\n*   **周囲への確認行動の期待は不明確:** 席を離れる際の周囲の状況確認や声かけといった行動が特に期待されていたかは明確に覚えていない。普段は大まかな確認程度に留まっている。\n\n**明らかなこと:** 今回のニアミスは、日頃の注意不足や習慣によるものと考えられます。\n\n**明らになったこと:**\n\n*   **顧客管理システムへのアクセス設定:** 特筆すべき特別なセキュリティ設定や注意点は顧客側には認識されていなかった。画面ロックの頻度は意識しているものの、毎回ではない。アクセス制限についても認識していなかった。\n*   **席の環境:** 顧客は、周囲の席との距離や壁の仕切りから、席が比較的プライベートな空間であると考えていた。\n**要約:**\n\n普段から自分の仕事に責任を持って取り組んでおり、特に顧客情報の取り扱いには細心の注意を払っている。今回のニアミスを経験したことで、情報セキュリティの重要性を再認識し、より一層意識と責任感が高まった。今後は、顧客情報の保護を最優先に、一つ一つの作業を丁寧に行うことを心がけている。\n\n## 要約\n\n**Question:** ニアミスを経験したことによる、ご自身の仕事に対する意識と責任感の変化、および日々の業務で特に心がけていること。\n\n**Reportから明らかなこと:**\n\n*   ニアミスを経験したことで、**仕事に対する意識と責任感が以前よりも高まった**。\n*   具体的には、以下の点に変化が見られる。\n    *   **細部への注意:** 作業後の画面の閉じなど、より細部にわたる注意を払うようになった。\n    *   **確認の徹底:** 顧客情報を取り扱う前に、必要な情報のみを表示しているか確認するなど、確認を徹底するようになった。\n    *   **周囲への配慮:** 顧客情報を取り扱う際に、周囲に人がいないか確認するなど、周囲への配慮を意識するようになった。\n*   日々業務で特に心がけていることは、以下の点である。\n    *   **情報セキュリティの原則の遵守**\n    *   **社内規定の遵守**\n    *   **情報セキュリティに関する知識・スキルの継続的な学習**\n\n\nこのレポートから、以下のことが明らかなりました。\n\n* **仕事へのモチベーション:** 普段から一定のモチベーションを維持している。\n* **モチベーションの源泉:**\n    * 顧客への貢献\n    * チームとの協力\n    * 自己成長\n* **仕事におけるやりがい:**\n    * 問題解決\n    * 成果の達成\n    * 顧客からの感謝\n\n## 要約\n\n**明らになったこと:**\n\n*   **全体的な業務への満足度は高い:** 仕事内容、チームの雰囲気、会社の制度に満足している。\n*   **満足している点:**\n    *   仕事内容にやりがいを感じている（顧客とのやり取り、データ分析など）。\n    *   チームメンバーとの協力体制が良好。\n    *   研修制度や福利厚生が充実している。\n*   **不満な点:**\n    *   一部業務がルーティン化し、マンネリ化を感じる。\n    *   部署間の情報共有が不足し、連携がうまくいかない。\n    *   評価制度が明確でなく、成果の評価が分かりにくい。\n*   **改善への意欲:** これらの点を改善することで、さらなる業務への満足度向上を目指している。\n\n## QuestionとReportからの主な知見\n\nこのQuestionとReportから、以下の点が明らかになりました。\n\n**全体的な状況:**\n\n*   普段の業務には全体的に満足している。\n*   仕事内容、チームの雰囲気、会社の制度には満足している。\n\n**改善点:**\n\n*   **ルーティン化された業務:** 顧客情報の入力・更新、請求書の作成、定型的なレポート作成が該当し、創造性や工夫の余地が少ないと感じている。\n*   **情報共有の不足:** 部署間の連携不足、会議前の情報共有不足、社内システムの使いづらさが課題。\n*   **評価制度の不明確さ:** 評価基準の不明確さ、評価タイミングの不透明さ、評価結果の説明不足が課題。\n*   **業務負荷:** 繁忙期に仕事量が増え、スケジュール管理が難しくなる。業務の優先順位が明確でないため、何から取り組むべきか迷うことがある。\n\n**要望:**\n\n*   ルーティン業務の自動化\n*   情報共有の促進\n*   評価制度の明確化\n*   業務の優先順位の明確化\n\n要するに、現状は満足度が高いものの、ルーティン業務の効率化、情報共有の改善、評価制度の透明化、そして優先順位の明確化によって、より創造的で効率的な業務遂行が可能になると考えている。\n\n## 要約\n\n**職場環境について:**\n\n*   **全体的に快適:** 物理的な環境と機器の両方において、快適に業務に取り組める状態だと感じている。\n*   **物理的な環境:** 席の広さ、明るさ、温度は十分で快適。騒音も許容範囲内。\n*   **PC・機器:** PCの動作、モニター、キーボード・マウスは問題なく、使いやすい。必要な機器も揃っている。\n\n**改善点:**\n\n*   椅子の快適性向上\n*   席の照明の調整機能\n*   コンセントの位置改善\n\n## 要約\n\n**職場環境について:**\n\n*   **現状:** 職場環境は快適に業務に取り組める状態であると認識されている。\n*   **改善要望:**\n    *   **椅子:** 長時間座っても疲れにくい、腰への負担が少ない椅子を希望。座面、奥行き、背もたれの調整機能があると良い。\n    *   **照明:** 明るさ調整可能なスイッチを希望。\n    *   **コンセント:** 席の近くへの増設または延長コード設置の配慮を希望。\n\n**業務に関する情報提供について:**\n\n*   **現状:** 全体的には適切だが、改善の余地がある。\n*   **改善要望:**\n    *   **タイミング:** 重要情報の提供タイミングを早める。\n    *   **整理:** 情報の整理を分かりやすくする（目的・背景の説明など）。\n    *   **手段:** メールだけでなく、社内SNSや掲示板など複数の情報提供手段を検討する。\n*   **特に課題:** 部署間の連携が必要な業務において、情報共有が不足している。営業部と事務部の顧客情報共有など、定期的な情報交換の機会を設けるべき。\n\n**結論:**\n\n従業員は現在の職場環境と情報提供に概ね満足しているものの、より快適で効率的な業務遂行のため、具体的な改善要望がある。特に、情報提供のタイミング、整理、手段の多様化、そして部署間の連携強化が重要である。\n\n## 明らかになったことのまとめ\n\nこのQuestionとReportから、以下の点が明らかになりました。\n\n* **人間関係は全体的に良好:** 同僚や上司との関係は良好であり、仕事上の相談や意見交換はしやすい。\n* **チームワークも良好:** 目標達成のために協力し合っている。\n* **改善点としてコミュニケーションの活性化を希望:** 定期的なチームミーティングや懇親会などを通じて、親睦を深めたいと考えている。\n* **意見の多様性の尊重を希望:** よりオープンな雰囲気で、様々な意見やアイデアが出せるようにしたい。\n* **感謝の言葉の交換を意識したい:** 日頃の感謝の気持ちを言葉で伝え合うことを意識したい。\n* **部署間の連携における情報共有の課題認識:** 部署間の連携が重要な業務において、情報共有の不足を感じている。\n* **情報共有の改善策を検討中:** 定期的な合同会議やチャットツールの活用など、情報共有を円滑にするための具体的な対策を検討している。\n\n要するに、**職場環境は良好だが、より一層の親睦とコミュニケーション、そして部署間の連携強化を望んでいる**ということがわかります。\n\n## まとめ\n\n**職場全体の雰囲気について、以下の点が明らかになりました。**\n\n* **全体的な印象:** ポジティブで活気がある。\n* **良い点:**\n    * 協調性が高く、助け合う文化がある。\n    * チームワークを重視し、互いに協力し合う。\n    * 新しいことに挑戦する精神を奨励し、成長を促す。\n    * 社員の自主性を尊重する。\n    * 福利厚生が充実している。\n* **改善点:**\n    * 部署間の連携が不十分で、情報共有が不足している。\n    * 全体的なコミュニケーションを活発化させたい。\n    * 評価制度の透明性を高めたい。\n    * ワークライフバランスの改善が必要。\n\n**全体として、職場環境は良好であり、仕事にやりがいを感じているものの、上記の改善点に取り組むことで、さらに働きやすい職場になる可能性があることが示唆されました。**\n\nこのレポートから、以下の点が明らかなりました。\n\n* **トレーニング:** 基本的なトレーニングは十分だが、業務変更や新システム導入への対応、外部研修機会の提供が不足している。より実践的なトレーニングと外部研修の機会を定期的に実施することで、業務効率の向上が期待できる。\n* **リスク管理:** 情報セキュリティに関する体制は整っているが、従業員一人ひとりの理解促進と、リスク発生時の対応手順の明確化・シミュレーションの実施が課題である。\n* **業務プロセス:** 業務効率化のためのシステムは導入されているが、一部手作業が残っており、自動化の余地がある。特に定型業務の自動化により、従業員はより創造的な業務に集中できる。\n* **部署運営方針:** 目標や役割は明確だが、進捗状況の可視化、目標設定の見直し、社員の意見反映の改善が望ましい。\n* **全体評価:** 全体的に職場環境は良好だが、上記の改善点に取り組むことで、より働きやすく、成果を出せる職場になる可能性がある。\n\nこのレポートから、以下の点が明らかなりました。\n\n* **意思決定プロセス:** 透明性はある程度あるものの、重要な決定の情報が限られているため、透明性向上が必要。社員の参加が限られており、より多くの意見を取り入れるべき。意思決定のスピードは状況によって異なり、権限委譲による迅速化が望ましい。\n* **情報開示:** 社内報やSNSでの情報共有はあるが、部署間の情報共有が不足している。情報の探しやすさや分かりやすさの改善が必要。上層部からの一方的な情報提供が中心で、双方向のコミュニケーションを促進する必要がある。\n* **コミュニケーション:** 上層部とのコミュニケーションは比較的円滑だが、気軽に意見交換できる雰囲気ではない。部門間の連携が不足しており、定期的な合同会議や交流イベントによる強化が望ましい。社員の意見や提案が意思決定に反映されにくい。\n* **経営理念・経営方針:** 社員の多くが共感できるが、組織全体への浸透が不十分。具体的な行動指針の不足がある。\n\n全体として、組織の成長と発展のためには、これらの課題への取り組みが重要であると認識されている。\n\n**明らになったこと:**\n\n*   **高いレベルでの組織へのコミットメント:** 報告者は、仕事への意欲、責任感、組織の目標達成への貢献意欲、組織への愛着といった点で高いコミットメントを感じている。\n*   **コミットメントを高める課題:** キャリアパスの不明確さ、評価制度の透明性の欠如、組織の方針の不明確さが、より高いレベルでのコミットメントを阻害している。\n*   **課題解決への意欲:** これらの課題が解決されれば、報告者はさらに積極的に組織に貢献したいと考えている。\n**明らになったこと:**\n\n今回のインタビューと業務を通して、ヒヤリハットやインシデントの原因として、以下の4つの主要な領域で課題があることが明確になりました。\n\n1. **業務プロセス:** 複雑な手順、手順の曖昧さ、作業負荷の偏りがヒヤリハットに繋がる要因となっている。\n2. **情報共有:** 情報伝達の遅延、情報の非対称性、情報の過多が問題となっている。\n3. **コミュニケーション:** コミュニケーション不足、誤解、上司への相談の躊躇が課題である。\n4. **組織文化:** リスクに対する意識の低さ、報告体制の不備、心理的安全性の欠如が問題となっている。\n\nこれらの要因は単独で存在するのではなく、複合的に絡み合ってヒヤリハットやインシデントを引き起こす可能性があることが示唆されています。\n\n**明らになったこと:**\n\n*   ヒヤリハットやインシデンツの発生要因は、業務プロセス、情報共有、コミュニケーション、組織文化の4つの側面から説明できる。\n*   各側面において、具体的な問題点として以下の点が挙げられる。\n    *   **業務プロセス:** 複雑な手順、手順の曖昧さ、作業負荷の偏り\n    *   **情報共有:** 情報伝達の遅延、情報の非対称性、情報の過多\n    *   **コミュニケーション:** コミュニケーション不足、誤解、上司への相談の躊躇\n    *   **組織文化:** リスク意識の低さ、報告体制の不備、心理的安全性の欠如\n*   これらの要因は単独でなく、複合的に絡み合ってヒヤリハットやインシデンツを引き起こす可能性がある。\n*   より具体的にするために、各要因について具体的な事例を付け加えることも考えられる。\n\n**要するに、ヒヤリハットやインシデンツの原因は多岐にわたり、組織全体の問題として捉える必要があることが明確になった。**\n']
    # final_summary = engine.generate_final_summary()
    # idx =5
    # turn_num =9
    # with open(f"Study_Output/SCENARIO_{idx}_Ollama_AIReN_turn_{turn_num}_{time.strftime('%Y%m%d_%H%M%S')}_debug.json", "w", encoding="utf-8") as f:
    #         json.dump(final_summary, f, ensure_ascii=False, indent=2)