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
from langchain_openai import ChatOpenAI
import fitz
from docx import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ==============================================
# ENVIRONMENT VALIDATION
# ==============================================
try:
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
except KeyError:
    st.error("🔑 OPENAI_API_KEY not found in environment variables")
    st.stop()

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
        ["Concise", "Balanced"],
        index=1,
        help="Control how condensed the summary should be"
    )
    
    # NOTE: These parameters are passed to generate_response but not used in the prompt template
    length_params = {
        "Concise": {"max_length": 80, "min_length": 40},
        "Balanced": {"max_length": 150, "min_length": 90},
    }
    
    st.header("📁 File Upload")
    uploaded_file = st.file_uploader(
        "Or upload a file",
        type=["pdf", "docx"],
        help="Supported formats: PDF, DOCX"
    )

# ==============================================
# TEXT INPUT HANDLING
# ==============================================
def extract_text_from_file(uploaded_file):
    """Extract text from uploaded PDF or DOCX file"""
    import io
    try:
        if uploaded_file.type == "application/pdf":
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            return text
            
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(io.BytesIO(uploaded_file.read()))
            return "\n".join([para.text for para in doc.paragraphs])
            
        else:
            st.warning("Unsupported file type")
            return None
            
    except Exception as e:
        logger.error(f"File extraction error: {str(e)}")
        st.error(f"⚠️ Failed to extract text: {str(e)}")
        return None

txt_input = st.text_area(
    '📋 Paste your content here', 
    '', 
    height=300,
    placeholder="Paste your article, report, or any text you want summarized..."
)

# Handle file content if uploaded
if uploaded_file is not None:
    with st.spinner('📄 Extracting text from document...'):
        extracted_text = extract_text_from_file(uploaded_file)
        if extracted_text:
            st.session_state.extracted_text = extracted_text
            st.session_state.use_file_content = True
            st.success("✅ Document extracted successfully!")
else:
    st.session_state.use_file_content = False

# Use extracted text if available
if 'extracted_text' in st.session_state and st.session_state.get('use_file_content', False):
    txt_input = st.session_state.extracted_text

# ==============================================
# TEXT STATISTICS DISPLAY
# ==============================================
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
        logger.info("Loading LangChain summarization pipeline...")
        llm = ChatOpenAI(
            openai_api_base="https://api.ai.it.ufl.edu",
            model_name="llama-3.3-70b-instruct",
            temperature=0.1,
            openai_api_key=OPENAI_API_KEY
        )

        prompt_template = """Generate a comprehensive and clear summary of the uploaded project report.
                    Use the best summarization method depending on the content structure — 
                    you may use bullet points, numbered lists, tables, or article-style paragraphs as 
                    appropriate to maximize clarity and conciseness.
                    
                    The summary should: 
                    Key Points Highlight the core ideas or arguments.
                    Include relevant supporting information or examples or Important Details  .
                    Summarize the overall insights or takeaways as conclusion .
                    Ensure clarity, logical flow, and avoid repeating the original wording directly.
                    Try to keep it short, easy to read, and informative — like something you'd 
                    share with a person who wants to quickly understand what the document was all about

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
# SUMMARY GENERATION
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
            
            # NOTE: The length parameters are passed but not used in the prompt template
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
