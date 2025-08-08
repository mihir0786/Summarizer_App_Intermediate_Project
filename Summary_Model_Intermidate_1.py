# ==============================================
# SETUP AND CONFIGURATION
# ==============================================
import os
import logging
import time
from dotenv import load_dotenv
import streamlit as st
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ==============================================
# STREAMLIT UI CONFIGURATION
# ==============================================
st.set_page_config(page_title='📝 Summarization Model', layout="centered")
st.title('📝 Text Summarization Application')
st.markdown("Transform lengthy documents into concise summaries using advanced NLP technology.")

# ==============================================
# USER PREFERENCES
# ==============================================
with st.sidebar:
    st.header("⚙️ Customization Panel")
    summary_length = st.selectbox(
        "Summary Density",
        ["Concise", "Balanced", "Detailed"],
        index=1,
        help="Control how condensed the summary should be"
    )
    
    # NOTE: These parameters are defined but not currently utilized in the summarization logic
    # This explains why summary length selection doesn't affect output
    length_params = {
        "Concise": {"max_length": 80, "min_length": 40},
        "Balanced": {"max_length": 150, "min_length": 90},
        "Detailed": {"max_length": 300, "min_length": 150}
    }

# ==============================================
# INPUT HANDLING
# ==============================================
txt_input = st.text_area(
    '📋 Paste your content here', 
    '', 
    height=300,
    placeholder="Paste your article, report, or any text you want summarized..."
)

if txt_input:
    char_count = len(txt_input)
    word_count = len(txt_input.split())
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Characters", char_count)
    with col2:
        st.metric("🔠 Words", word_count)
    with col3:
        st.metric("⏱ Est. Time", f"{max(2, word_count // 100)} sec")
    
    if char_count < 100:
        st.warning("ℹ️ Longer texts generally produce better summaries")

# ==============================================
# MODEL CONFIGURATION
# ==============================================
@st.cache_resource(show_spinner=False)
def load_summarizer():
    """Initialize LangChain summarization pipeline"""
    try:
        OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
        llm = ChatOpenAI(
            openai_api_base="https://api.ai.it.ufl.edu",
            model_name="llama-3.3-70b-instruct",
            temperature=0.1,
            openai_api_key=OPENAI_API_KEY
        )

        prompt_template = """You are given a detailed passage. Write a well-structured and non-repetitive 
                    summary with the following sections:
                        1. **Key Points** – Highlight the core ideas or arguments.
                        2. **Important Details** – Include relevant supporting information or examples.
                        3. **Main Conclusions** – Summarize the overall insights or takeaways.
                    Ensure clarity, logical flow, and avoid repeating the original wording directly.

                    Text to summarize:{text}

                    Summary:"""

        prompt = PromptTemplate(
            input_variables=["text"],
            template=prompt_template
        )
        
        return LLMChain(
            llm=llm,
            prompt=prompt,
            verbose=True
        )
    except Exception as e:
        logger.error(f"Initialization failed: {str(e)}")
        st.error(f"🚨 Model initialization failed: {str(e)}")
        return None

# ==============================================
# RESPONSE GENERATION
# ==============================================
@st.cache_data(ttl=3600, show_spinner=False)
def generate_response(txt, max_len, min_len):
    """Generate unified summary of input text"""
    if not txt or not txt.strip():
        return "Please enter valid text"
    
    try:
        chain = load_summarizer()
        if not chain:
            return "⚙️ Model unavailable"
        
        with st.spinner('Creating summary...'):
            summary = chain.run(text=txt)
            return summary.replace("Summary:", "").strip()
            
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return f"⚠️ Error: {str(e)}"

# ==============================================
# MAIN APPLICATION FLOW
# ==============================================
with st.form(key='summary_form'):
    submitted = st.form_submit_button('🚀 Generate Summary')
    
    if submitted:
        if not txt_input.strip():
            st.warning("📝 Please enter text before submitting")
        else:
            start_time = time.time()
            params = length_params[summary_length]
            
            # NOTE: max_len/min_len are passed but not used in the prompt template
            with st.spinner(f'✨ Crafting {summary_length.lower()} summary...'):
                response = generate_response(txt_input, params["max_length"], params["min_length"])
                processing_time = time.time() - start_time
            
            st.session_state.last_summary = response
            st.session_state.summary_generated = True
            st.success(f"✅ Summary ready! ({processing_time:.1f}s)")

# ==============================================
# OUTPUT DISPLAY
# ==============================================
if st.session_state.get('summary_generated', False):
    st.divider()
    st.subheader("📄 Summary Output")
    
    with st.expander("View Formatted Summary", expanded=True):
        if 'last_summary' in st.session_state:
            st.write(st.session_state.last_summary)
        else:
            st.warning("No summary available")
    
    if 'last_summary' in st.session_state:
        st.download_button(
            label="💾 Save as TXT",
            data=st.session_state.last_summary,
            file_name="summary.txt",
            mime="text/plain"
        )