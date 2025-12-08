# AI Tutee - Learning by Teaching Data Visualization

An educational tool that helps learners practice teaching data visualization concepts to an AI student. Based on the evidence-based "learning by teaching" paradigm.

## What's New: Teacher-Driven Question Selection

The interface now follows a pedagogically-sound workflow where **you, the teacher, drive the learning process**:

1. **Pre-Test Assessment**: The AI student takes a diagnostic pre-test
2. **Review Results**: You see which questions the AI student got right/wrong
3. **Select What to Teach**: Click on any question to start a teaching conversation about that topic
4. **Teach Through Dialogue**: The AI student asks questions and expresses confusion—guide them to understanding
5. **Mark Progress**: When satisfied, mark the question as addressed and select another
6. **Post-Test**: Run a post-test to measure the AI student's improvement

This approach gives you agency over the learning flow, aligning with how real tutoring works.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Password Protection (Optional)
For deployed instances, you can add password protection to prevent unauthorized access:
```bash
# In your .env file, set:
AITUTEE_PASSWORD=your-secret-password
```
When set, users must enter this password to access the application. If not set, the app is accessible without a password.

### 4. Run the Application
```bash
streamlit run app/main_streamlit.py
```

## User Interface Flow

### Phase 1: Setup
- Select a teaching scenario (data types, chart selection, etc.)
- Choose the AI student's knowledge level (beginner, intermediate, advanced)
- Click "Start Session"

### Phase 2: Pre-Test Review
After the AI student takes the pre-test, you'll see:
- **Summary metrics**: Total questions, correct/incorrect counts
- **Question cards**: Each question shows whether the AI got it right or wrong
- **Action buttons**: Click "Teach" on any question to start a conversation

### Phase 3: Teaching
When you select a question:
- The AI student explains their (often flawed) reasoning
- They ask clarifying questions based on their misconceptions
- You teach by explaining, correcting, and providing examples
- The conversation continues until you're satisfied

**Sidebar controls**:
- "Done with this question" - Mark complete and return to question list
- "Back to Questions" - Return without marking complete
- "End & Post-Test" - Finish teaching and measure improvement

### Phase 4: Results
After the post-test, you'll see:
- Score comparison (pre-test vs post-test)
- Improvement metrics
- Learning summary (what the AI student learned)
- Detailed question-by-question breakdown

## Teaching Scenarios

1. **Identification of Data Types**
   - Categorical vs numerical data
   - Ordinal vs nominal distinctions
   - Recognizing identifier fields

2. **Connecting Data Types to Charts**
   - Matching data to appropriate chart families
   - Understanding composition constraints
   - Avoiding common mismatches (e.g., line charts for categories)

3. **Matching Charts to Analytical Tasks**
   - Aligning visualizations with analytical goals
   - Trend analysis, comparison, distribution, correlation
   - Task-driven chart selection

4. **Data Preparation for Visualization**
   - Cleaning and standardizing data
   - Handling missing values
   - Aggregation and reshaping

## Knowledge Levels

- **Beginner**: Strong misconceptions, struggles with fundamentals. Expect many wrong answers on pre-test.
- **Intermediate**: Partial understanding, some misconceptions. Mix of right and wrong answers.
- **Advanced**: Mostly correct, subtle misconceptions in edge cases.

## Project Structure

```
ai_tutee/
├── app/
│   ├── main_streamlit.py      # Main Streamlit application
│   ├── prompts/
│   │   └── system_ai_student.md   # AI student persona prompt
│   ├── scenarios/
│   │   ├── data_types.yaml
│   │   ├── type_to_chart.yaml
│   │   ├── chart_to_task.yaml
│   │   └── data_preparation.yaml
│   └── util/
│       ├── assessment.py      # Pre/post test logic
│       ├── io.py              # File I/O utilities
│       └── prompt_loader.py   # Prompt templating
├── logs/
│   └── runs/                  # Session transcripts
├── requirements.txt
└── .env.example
```

## Session Logging

All sessions are automatically logged to `logs/runs/` with:
- Full conversation transcript (JSONL format)
- Session summary with scores and metadata (JSON format)

## Tips for Effective Teaching

1. **Focus on incorrect answers**: These reveal misconceptions that need correction
2. **Ask the AI student to explain their reasoning**: This helps identify the root cause of confusion
3. **Use concrete examples**: The AI student learns better with specific scenarios
4. **Be patient**: Real learning takes multiple exchanges—don't expect instant understanding
5. **Check understanding**: Ask the AI student to apply what they learned to a new example

## Contributing

This is a prototype for educational research. Feedback and contributions welcome!