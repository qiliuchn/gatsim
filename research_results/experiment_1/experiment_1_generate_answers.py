"""
AI agent generate answers to questions for experiment 1.


Step 1:
load the questions from the folder `experiment_1_questions_with_context/`; each text file corresponds to one question.
store in a dictionary named "questions", with the following key, value pairs:
key: file name, like "question1.txt"
value: question content (string)


Step 2:
Invoke llm_generate to answer the question:
ai_answer = llm_generate_with_json_extraction_and_retries(question_content)

then extract "plan" from the answer:
ai_answer = ai_answer["plan"]


Step 3:
Save the answers to the file: `experiment_1_answers.json`.
Format:
[
    {
        "question_with_context": "question1.txt",
        "ai_answer": "answer1",
        "human_answer": ""
    },
    {
        "question_with_context": "question2.txt",
        "ai_answer": "answer2",
        "human_answer": ""
    }
]
Namely, "ai_answer" is the answer generated above.
"human_answer" is the answer to be provided by the user. Just leave it empty for now.
"""


import os
import json
from gatsim.agent.llm_modules.llm import llm_generate_with_json_extraction_and_retries

def main():
    # Step 1: Load questions from the folder
    questions_folder = "experiment_1_questions_with_context/"
    questions = {}
    
    # Check if the folder exists
    if not os.path.exists(questions_folder):
        print(f"Error: Folder '{questions_folder}' does not exist.")
        return
    
    # Load all text files from the folder
    for filename in os.listdir(questions_folder):
        if filename.endswith('.txt'):
            filepath = os.path.join(questions_folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    questions[filename] = file.read().strip()
                print(f"Loaded question from {filename}")
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    
    if not questions:
        print("No .txt files found in the questions folder.")
        return
    
    print(f"Loaded {len(questions)} questions total.")
    
    
    # Step 2: Generate AI answers for each question
    results = []
    
    for question_file, question_content in questions.items():
        print(f"Processing {question_file}...")
        
        try:
            # Generate answer using the LLM
            ai_response = llm_generate_with_json_extraction_and_retries(question_content)
            
            # Extract "plan" from the answer
            if isinstance(ai_response, dict) and "plan" in ai_response:
                ai_answer = ai_response["plan"]
            else:
                print(f"Warning: No 'plan' key found in response for {question_file}")
                ai_answer = str(ai_response)  # Fallback to full response
            
            # Create result entry
            result_entry = {
                "question_with_context": question_file,
                "ai_answer": ai_answer,
                "human_answer": ""
            }
            
            results.append(result_entry)
            print(f"Successfully processed {question_file}")
            
        except Exception as e:
            print(f"Error processing {question_file}: {e}")
            # Add entry with error message
            result_entry = {
                "question_with_context": question_file,
                "ai_answer": f"Error: {str(e)}",
                "human_answer": ""
            }
            results.append(result_entry)
    
    
    # Step 3: Save answers to JSON file
    output_file = "experiment_1_answers.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(results, file, indent=4, ensure_ascii=False)
        print(f"Results saved to {output_file}")
        print(f"Processed {len(results)} questions total.")
        
    except Exception as e:
        print(f"Error saving results to {output_file}: {e}")

if __name__ == "__main__":
    main()