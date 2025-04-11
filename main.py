import streamlit as st
from datetime import datetime
import json
import os
from pathlib import Path
import pandas as pd
from textblob import TextBlob
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import plotly.express as px
import base64
from PIL import Image
import io
import time
import hashlib
import uuid
from st_aggrid import AgGrid, GridOptionsBuilder
import numpy as np
from collections import Counter
import re
import tempfile
import plotly.io as pio
import markdown
from bs4 import BeautifulSoup
import html2text
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import emoji
import requests
import shutil

# --- App Config ---
st.set_page_config(
    page_title="Advanced Diary App",
    page_icon="📔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Path Setup ---
DIARY_DIR = Path("diary_entries")
DIARY_DIR.mkdir(exist_ok=True)
ENTRIES_FILE = DIARY_DIR / "entries.json"
KEY_FILE = DIARY_DIR / ".encryption_key"
PASSKEY_FILE = DIARY_DIR / ".passkey"

# --- Encryption Setup ---
def get_encryption_key():
    """Generate or load encryption key"""
    if not KEY_FILE.exists():
        key = base64.urlsafe_b64encode(os.urandom(32))
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        return key
    else:
        with open(KEY_FILE, "rb") as f:
            return f.read()

ENCRYPTION_KEY = get_encryption_key()

def encrypt_data(data):
    """Simple encryption for diary content"""
    if not data:
        return data
    try:
        # First encode as UTF-8, then base64
        data_bytes = data.encode('utf-8')
        return base64.urlsafe_b64encode(data_bytes).decode('utf-8')
    except Exception:
        # If encryption fails, return original data
        return data

def decrypt_data(encrypted_data):
    """Decrypt diary content"""
    if not encrypted_data:
        return encrypted_data
    try:
        # Try to decode as base64 first
        return base64.urlsafe_b64decode(encrypted_data.encode('utf-8')).decode('utf-8')
    except Exception:
        # If decryption fails, return original data
        return encrypted_data

# --- Passkey Setup ---
def hash_passkey(passkey):
    """Hash the passkey for secure storage"""
    return hashlib.sha256(passkey.encode()).hexdigest()

def verify_passkey(passkey):
    """Verify if the provided passkey is correct"""
    if not PASSKEY_FILE.exists():
        return False
    
    with open(PASSKEY_FILE, "r") as f:
        stored_hash = f.read().strip()
    
    return hash_passkey(passkey) == stored_hash

def setup_passkey():
    """Set up the passkey for the diary"""
    if PASSKEY_FILE.exists():
        return True
    
    st.title("🔒 Set Up Your Diary Passkey")
    st.info("Create a passkey to secure your diary. You'll need this to edit or delete entries.")
    
    with st.form("passkey_form"):
        passkey = st.text_input("Enter Passkey", type="password")
        confirm_passkey = st.text_input("Confirm Passkey", type="password")
        submit = st.form_submit_button("Set Passkey")
        
        if submit:
            if not passkey:
                st.error("Passkey cannot be empty")
                return False
            
            if passkey != confirm_passkey:
                st.error("Passkeys do not match")
                return False
            
            # Save the hashed passkey
            with open(PASSKEY_FILE, "w") as f:
                f.write(hash_passkey(passkey))
            
            st.success("Passkey set successfully!")
            time.sleep(1)
            st.rerun()
    
    return False

def verify_passkey_input():
    """Ask user to enter passkey for verification"""
    with st.form("verify_passkey_form"):
        passkey = st.text_input("Enter Your Passkey", type="password")
        submit = st.form_submit_button("Verify")
        
        if submit:
            if verify_passkey(passkey):
                st.session_state['passkey_verified'] = True
                st.success("Passkey verified!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Incorrect passkey")
                # Don't return False here, let the form stay visible
    
    return False

# --- Initialize JSON File ---
if not ENTRIES_FILE.exists():
    with open(ENTRIES_FILE, "w") as f:
        json.dump([], f)

# --- Helper Functions ---
def load_entries():
    """Load all entries from JSON file with decryption"""
    try:
        with open(ENTRIES_FILE, "r") as f:
            entries = json.load(f)
            if not isinstance(entries, list):
                entries = []
            for entry in entries:
                entry['content'] = decrypt_data(entry['content'])
            return entries
    except Exception as e:
        st.error(f"Error loading entries: {str(e)}")
        return []

def save_entries(entries):
    """Save entries to JSON file with encryption"""
    if not isinstance(entries, list):
        entries = []
    entries_to_save = []
    for entry in entries:
        entry_copy = entry.copy()
        entry_copy['content'] = encrypt_data(entry['content'])
        entries_to_save.append(entry_copy)
    
    try:
        with open(ENTRIES_FILE, "w") as f:
            json.dump(entries_to_save, f, indent=2)
    except Exception as e:
        st.error(f"Error saving entries: {str(e)}")

def analyze_sentiment(text):
    """Get sentiment score (-1 to 1) with enhanced analysis"""
    analysis = TextBlob(text)
    # Additional metrics
    subjectivity = analysis.sentiment.subjectivity
    word_count = len(text.split())
    return {
        'polarity': analysis.sentiment.polarity,
        'subjectivity': subjectivity,
        'word_count': word_count
    }

def create_wordcloud(text):
    """Generate a word cloud with custom styling"""
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color="white",
        colormap='viridis',
        max_words=100,
        stopwords=None,
        min_font_size=10
    ).generate(text)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation="bilinear")
    ax.axis("off")
    plt.tight_layout()
    return fig

def mood_timeline(df):
    """Enhanced mood timeline with moving average"""
    df['moving_avg'] = df['sentiment'].rolling(window=3, min_periods=1).mean()
    
    fig = px.line(df, x='date', y=['sentiment', 'moving_avg'], 
                 title='Mood Timeline with Trend',
                 labels={'value': 'Sentiment Score', 'date': 'Date'},
                 color_discrete_map={'sentiment': '#636EFA', 'moving_avg': '#FFA15A'})
    
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor='rgba(0,0,0,0)',
        legend_title_text='Metric'
    )
    return fig

def analyze_writing_habits(df):
    """Analyze writing patterns"""
    df['day_of_week'] = df['date'].dt.day_name()
    df['hour'] = df['date'].dt.hour
    df['month'] = df['date'].dt.month_name()
    
    # Most active days
    day_counts = df['day_of_week'].value_counts().reset_index()
    day_counts.columns = ['Day', 'Entries']
    
    # Most active hours
    hour_counts = df['hour'].value_counts().reset_index()
    hour_counts.columns = ['Hour', 'Entries']
    
    return day_counts, hour_counts

def extract_keywords(text, n=10):
    """Extract most common keywords (excluding stopwords)"""
    words = re.findall(r'\b\w{3,}\b', text.lower())
    stopwords = set(['the', 'and', 'that', 'have', 'for', 'not', 'with', 'this', 'but', 'just'])
    words = [word for word in words if word not in stopwords]
    return Counter(words).most_common(n)

def convert_markdown_to_text(markdown_text):
    """Convert markdown to plain text for PDF"""
    # First convert markdown to HTML
    html = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])
    
    # Then convert HTML to plain text while preserving some formatting
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0  # No wrapping
    text = h.handle(html)
    
    # Clean up any remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    return text

def convert_markdown_to_pdf_content(text):
    """Convert markdown text to properly formatted PDF content"""
    # Remove any existing HTML-like tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Handle basic markdown formatting
    formatted_text = text
    
    # Handle code blocks first (save them to preserve from other formatting)
    code_blocks = []
    def save_code(match):
        code_blocks.append(match.group(1))
        return f"CODE_BLOCK_{len(code_blocks)-1}"
    
    formatted_text = re.sub(r'`([^`]+)`', save_code, formatted_text)
    
    # Handle bold text (handle both ** and __ syntax)
    bold_blocks = []
    def save_bold(match):
        bold_blocks.append(match.group(1))
        return f"BOLD_BLOCK_{len(bold_blocks)-1}"
    
    formatted_text = re.sub(r'\*\*([^\*]+)\*\*', save_bold, formatted_text)
    formatted_text = re.sub(r'__([^_]+)__', save_bold, formatted_text)
    
    # Handle italic text (handle both * and _ syntax)
    italic_blocks = []
    def save_italic(match):
        italic_blocks.append(match.group(1))
        return f"ITALIC_BLOCK_{len(italic_blocks)-1}"
    
    formatted_text = re.sub(r'\*([^\*]+)\*', save_italic, formatted_text)
    formatted_text = re.sub(r'_([^_]+)_', save_italic, formatted_text)
    
    # Handle lists
    formatted_text = re.sub(r'^\s*[\-\*]\s+(.+)$', r'• \1', formatted_text, flags=re.MULTILINE)
    formatted_text = re.sub(r'^\s*(\d+)\.\s+(.+)$', r'\1. \2', formatted_text, flags=re.MULTILINE)
    
    # Clean up any remaining special characters
    formatted_text = (formatted_text
        .replace('&lt;', '<')
        .replace('&gt;', '>')
        .replace('&amp;', '&')
        .replace('&quot;', '"')
        .replace('&apos;', "'")
        .replace('\\', '')
    )
    
    # Restore code blocks
    for i, code in enumerate(code_blocks):
        formatted_text = formatted_text.replace(
            f"CODE_BLOCK_{i}",
            f'<font face="Courier">{code}</font>'
        )
    
    # Restore bold blocks
    for i, bold in enumerate(bold_blocks):
        formatted_text = formatted_text.replace(
            f"BOLD_BLOCK_{i}",
            f'<b>{bold}</b>'
        )
    
    # Restore italic blocks
    for i, italic in enumerate(italic_blocks):
        formatted_text = formatted_text.replace(
            f"ITALIC_BLOCK_{i}",
            f'<i>{italic}</i>'
        )
    
    return formatted_text

def setup_fonts():
    """Download and setup DejaVu fonts for PDF generation"""
    fonts_dir = Path("fonts")
    fonts_dir.mkdir(exist_ok=True)
    
    # Updated URLs to the correct DejaVu font repository
    font_files = {
        'DejaVuSansCondensed.ttf': 'https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSansCondensed.ttf',
        'DejaVuSansCondensed-Bold.ttf': 'https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSansCondensed-Bold.ttf',
        'DejaVuSansCondensed-Oblique.ttf': 'https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSansCondensed-Oblique.ttf'
    }
    
    for font_file, url in font_files.items():
        font_path = fonts_dir / font_file
        if not font_path.exists():
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                with open(font_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
            except Exception as e:
                st.error(f"Error downloading font {font_file}: {str(e)}")
                return False
    return True

def generate_pdf(selected_entries):
    """Generate a beautiful PDF of selected diary entries using reportlab"""
    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        pdf_path = tmp.name
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        alignment=1
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading3'],
        fontSize=14,
        spaceAfter=12
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        allowWidows=0,
        allowOrphans=0
    )
    code_style = ParagraphStyle(
        'CustomCode',
        parent=styles['Code'],
        fontSize=10,
        fontName='Courier',
        spaceAfter=8,
        allowWidows=0,
        allowOrphans=0,
        backColor=colors.lightgrey,
        borderPadding=5
    )
    
    # Prepare the story (content) for the PDF
    story = []
    temp_files = []  # Keep track of temporary files
    
    try:
        # Add cover page
        story.append(Paragraph("My Personal Diary", title_style))
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
        story.append(Paragraph(f"Selected Entries: {len(selected_entries)}", subtitle_style))
        story.append(Spacer(1, 50))
        
        # Add entries
        for entry in selected_entries:
            # Add page break between entries
            if len(story) > 0:
                story.append(PageBreak())
            
            # Entry title
            title = convert_markdown_to_pdf_content(entry['title'])
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 12))
            
            # Date and mood
            mood_text = emoji.demojize(entry['mood'], delimiters=('(', ')'))
            story.append(Paragraph(f"Date: {entry['date']} | Mood: {mood_text}", normal_style))
            
            # Tags
            tags = [tag for tag in entry['tags']]  # No need to convert tags
            tags_text = ", ".join(tags)
            story.append(Paragraph(f"Tags: {tags_text}", normal_style))
            story.append(Spacer(1, 12))
            
            # Content
            content = entry['content']
            paragraphs = content.split('\n')
            
            in_code_block = False
            code_block_content = []
            
            for para in paragraphs:
                if para.strip():
                    if para.startswith('```'):
                        if in_code_block:
                            # End of code block
                            code_text = '\n'.join(code_block_content)
                            story.append(Paragraph(code_text, code_style))
                            code_block_content = []
                            in_code_block = False
                        else:
                            # Start of code block
                            in_code_block = True
                    elif in_code_block:
                        code_block_content.append(para)
                    elif para.startswith('# '):
                        story.append(Paragraph(para[2:].strip(), title_style))
                    elif para.startswith('## '):
                        story.append(Paragraph(para[3:].strip(), subtitle_style))
                    elif para.startswith('### '):
                        story.append(Paragraph(para[4:].strip(), heading_style))
                    else:
                        formatted_para = convert_markdown_to_pdf_content(para)
                        story.append(Paragraph(formatted_para, normal_style))
                    
                    if not in_code_block:
                        story.append(Spacer(1, 6))
            
            # Handle any remaining code block
            if code_block_content:
                code_text = '\n'.join(code_block_content)
                story.append(Paragraph(code_text, code_style))
            
            # Add image if available
            if entry.get('image'):
                try:
                    # Create a temporary file for the image
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as img_tmp:
                        img_path = img_tmp.name
                        temp_files.append(img_path)  # Add to list of temp files
                        img_bytes = base64.b64decode(entry['image'])
                        with open(img_path, 'wb') as f:
                            f.write(img_bytes)
                    
                    # Add image to PDF
                    if os.path.exists(img_path) and os.path.getsize(img_path) > 0:
                        img = RLImage(img_path, width=6*inch, height=4*inch)
                        story.append(Spacer(1, 12))
                        story.append(img)
                        story.append(Paragraph("Attached Image", normal_style))
                except Exception as e:
                    story.append(Paragraph(f"Image could not be included: {str(e)}", normal_style))
        
        # Build the PDF
        doc.build(story)
        return pdf_path
        
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        return None
        
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                print(f"Warning: Could not delete temporary file {temp_file}: {e}")

# --- Main App Functions ---
def write_entry():
    """Enhanced entry writing with writing analysis"""
    st.title("✍️ New Entry")
    
    # Initialize session state for form submission
    if 'form_submitted' not in st.session_state:
        st.session_state['form_submitted'] = False
    
    # Initialize session state for form values
    if 'form_values' not in st.session_state:
        st.session_state['form_values'] = {
            'title': '',
            'content': '',
            'date': datetime.now(),
            'mood': '🙂',
            'tags': [],
            'image': None,
            'entry_passkey': ''
        }
    
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            title = st.text_input("Title", 
                                value=st.session_state['form_values']['title'],
                                placeholder="Entry title...")
            content = st.text_area("Your Thoughts", 
                                 value=st.session_state['form_values']['content'],
                                 height=300, 
                                 placeholder="Write freely...",
                                 help="Your private space for reflection. Supports Markdown formatting!")
            
            # Add entry passkey field
            entry_passkey = st.text_input("Entry Passkey", 
                                        type="password",
                                        value=st.session_state['form_values']['entry_passkey'],
                                        help="Create a unique passkey for this entry. You'll need this to edit or delete this entry later.")
            
            # Add Markdown help
            with st.expander("Markdown Help"):
                st.markdown("""
                ### Markdown Formatting
                You can use Markdown to format your diary entries:
                
                - **Bold text**: `**bold**`
                - *Italic text*: `*italic*`
                - # Heading 1: `# Heading`
                - ## Heading 2: `## Subheading`
                - ### Heading 3: `### Minor heading`
                - Bullet points: `* item` or `- item`
                - Numbered lists: `1. First item`
                - [Links](https://example.com): `[Link text](URL)`
                - `Code`: `` `code` ``
                
                Your formatting will be preserved in the PDF when you download it.
                """)
            
        with col2:
            date = st.date_input("Date", value=st.session_state['form_values']['date'])
            mood = st.select_slider("Mood", 
                                  options=["😭", "😔", "😐", "🙂", "😊", "😄"],
                                  value=st.session_state['form_values']['mood'])
            tags = st.multiselect("Tags", 
                                ["Personal", "Work", "Ideas", "Goals", 
                                 "Reflections", "Gratitude", "Challenges"],
                                default=st.session_state['form_values']['tags'])
            
            # Image upload with preview
            uploaded_image = st.file_uploader("Add Image", 
                                            type=["jpg", "png", "jpeg"],
                                            accept_multiple_files=False)
        
        submitted = st.form_submit_button("Save Entry", use_container_width=True)
        
        if submitted:
            # Validate required fields
            validation_errors = []
            
            if not title:
                validation_errors.append("Title is required")
            
            if not content:
                validation_errors.append("Content is required")
            
            if not tags:
                validation_errors.append("At least one tag is required")
                
            if not entry_passkey:
                validation_errors.append("Entry passkey is required")
            
            # Display validation errors if any
            if validation_errors:
                st.error("\n".join(validation_errors))
                st.session_state['form_submitted'] = False
                
                # Save current form values to session state
                st.session_state['form_values'] = {
                    'title': title,
                    'content': content,
                    'date': date,
                    'mood': mood,
                    'tags': tags,
                    'image': uploaded_image,
                    'entry_passkey': entry_passkey
                }
                return
            
            # If validation passes, set form_submitted to True
            st.session_state['form_submitted'] = True
            
            # Analyze content
            sentiment = analyze_sentiment(content)
            keywords = extract_keywords(content)
            
            # Handle image
            image_data = None
            if uploaded_image:
                image_data = base64.b64encode(uploaded_image.read()).decode("utf-8")
            
            # Create entry
            new_entry = {
                "id": str(uuid.uuid4()),
                "date": str(date),
                "timestamp": datetime.now().isoformat(),
                "title": title,
                "content": content,
                "mood": mood,
                "tags": tags,
                "sentiment": sentiment['polarity'],
                "subjectivity": sentiment['subjectivity'],
                "word_count": sentiment['word_count'],
                "keywords": [kw[0] for kw in keywords],
                "image": image_data,
                "passkey_hash": hash_passkey(entry_passkey)
            }
            
            # Save entry
            entries = load_entries()
            entries.append(new_entry)
            save_entries(entries)
            
            # Store analysis in session state to persist after rerun
            st.session_state['last_entry_analysis'] = {
                'word_count': sentiment['word_count'],
                'sentiment': sentiment['polarity'],
                'subjectivity': sentiment['subjectivity'],
                'keywords': keywords
            }
            
            # Reset form values
            st.session_state['form_values'] = {
                'title': '',
                'content': '',
                'date': datetime.now(),
                'mood': '🙂',
                'tags': [],
                'image': None,
                'entry_passkey': ''
            }
            
            st.success("Entry saved successfully!")
    
    # Show success message if form was submitted successfully
    if st.session_state['form_submitted']:
        st.session_state['form_submitted'] = False
    
    # Show analysis from last entry if available
    if 'last_entry_analysis' in st.session_state:
        with st.expander("Last Entry Analysis", expanded=True):
            analysis = st.session_state['last_entry_analysis']
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Word Count", analysis['word_count'])
                st.metric("Sentiment", f"{analysis['sentiment']:.2f}")
                st.metric("Subjectivity", f"{analysis['subjectivity']:.2f}")
            
            with col2:
                st.write("**Top Keywords:**")
                for kw in analysis['keywords']:
                    st.write(f"- {kw[0]} (used {kw[1]} times)")

def verify_entry_passkey(entry):
    """Verify the passkey for a specific entry"""
    with st.form("entry_passkey_form"):
        passkey = st.text_input("Enter Entry Passkey", type="password")
        submit = st.form_submit_button("Verify")
        
        if submit:
            if hash_passkey(passkey) == entry['passkey_hash']:
                st.session_state['passkey_verified'] = True
                st.success("Passkey verified!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Incorrect passkey")
                return False
    return False

def edit_entry(entry):
    """Edit an existing diary entry"""
    st.title("✏️ Edit Entry")
    
    # Initialize session state for form submission
    if 'edit_form_submitted' not in st.session_state:
        st.session_state['edit_form_submitted'] = False
    
    # Initialize session state for form values
    if 'edit_form_values' not in st.session_state:
        st.session_state['edit_form_values'] = {
            'title': entry['title'],
            'content': entry['content'],
            'date': datetime.strptime(entry['date'], '%Y-%m-%d'),
            'mood': entry['mood'],
            'tags': entry['tags'],
            'image': None
        }
    
    # Check if passkey is verified
    if 'passkey_verified' not in st.session_state or not st.session_state['passkey_verified']:
        st.warning("🔒 Please enter the entry passkey to edit this entry")
        if verify_entry_passkey(entry):
            return
        return
    
    # Handle image removal outside the form
    if entry.get('image'):
        st.write("Current Image:")
        img_bytes = base64.b64decode(entry['image'])
        st.image(Image.open(io.BytesIO(img_bytes)), width=200)
        if st.button("Remove Image"):
            entry['image'] = None
            st.success("Image removed!")
            time.sleep(1)
            st.rerun()
    else:
        st.info("No image attached")
    
    with st.form("edit_form", clear_on_submit=False):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            title = st.text_input("Title", value=st.session_state['edit_form_values']['title'])
            content = st.text_area("Your Thoughts", 
                                 value=st.session_state['edit_form_values']['content'], 
                                 height=300)
            
            # Add Markdown help
            with st.expander("Markdown Help"):
                st.markdown("""
                ### Markdown Formatting
                You can use Markdown to format your diary entries:
                
                - **Bold text**: `**bold**`
                - *Italic text*: `*italic*`
                - # Heading 1: `# Heading`
                - ## Heading 2: `## Subheading`
                - ### Heading 3: `### Minor heading`
                - Bullet points: `* item` or `- item`
                - Numbered lists: `1. First item`
                - [Links](https://example.com): `[Link text](URL)`
                - `Code`: `` `code` ``
                
                Your formatting will be preserved in the PDF when you download it.
                """)
        
        with col2:
            date = st.date_input("Date", value=st.session_state['edit_form_values']['date'])
            mood = st.select_slider("Mood", 
                                  options=["😭", "😔", "😐", "🙂", "😊", "😄"],
                                  value=st.session_state['edit_form_values']['mood'])
            tags = st.multiselect("Tags", 
                                ["Personal", "Work", "Ideas", "Goals", 
                                 "Reflections", "Gratitude", "Challenges"],
                                default=st.session_state['edit_form_values']['tags'])
            
            # Image upload with preview
            uploaded_image = st.file_uploader("Upload New Image", 
                                            type=["jpg", "png", "jpeg"],
                                            accept_multiple_files=False)
        
        # Form submit buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            save_button = st.form_submit_button("Save Changes", use_container_width=True)
        with col2:
            cancel_button = st.form_submit_button("Cancel", use_container_width=True)
        
        if save_button:
            # Validate required fields
            validation_errors = []
            
            if not title:
                validation_errors.append("Title is required")
            
            if not content:
                validation_errors.append("Content is required")
            
            if not tags:
                validation_errors.append("At least one tag is required")
            
            # Display validation errors if any
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
                st.session_state['edit_form_submitted'] = False
                
                # Save current form values to session state
                st.session_state['edit_form_values'] = {
                    'title': title,
                    'content': content,
                    'date': date,
                    'mood': mood,
                    'tags': tags,
                    'image': uploaded_image
                }
                return
            
            # If validation passes, set edit_form_submitted to True
            st.session_state['edit_form_submitted'] = True
            
            # Analyze content
            sentiment = analyze_sentiment(content)
            keywords = extract_keywords(content)
            
            # Handle image
            image_data = entry.get('image')
            if uploaded_image:
                image_data = base64.b64encode(uploaded_image.read()).decode("utf-8")
            
            # Update entry
            entry['date'] = str(date)
            entry['title'] = title
            entry['content'] = content
            entry['mood'] = mood
            entry['tags'] = tags
            entry['sentiment'] = sentiment['polarity']
            entry['subjectivity'] = sentiment['subjectivity']
            entry['word_count'] = sentiment['word_count']
            entry['keywords'] = [kw[0] for kw in keywords]
            entry['image'] = image_data
            entry['last_edited'] = datetime.now().isoformat()
            
            # Save updated entries
            entries = load_entries()
            for i, e in enumerate(entries):
                if e['id'] == entry['id']:
                    entries[i] = entry
                    break
            save_entries(entries)
            
            # Set flag to redirect to view entries
            st.session_state['redirect_to_view'] = True
            
            time.sleep(1)
            st.rerun()
        
        elif cancel_button:
            st.info("Editing cancelled")
            time.sleep(1)
            st.rerun()
    
    # Show success message if form was submitted successfully
    if st.session_state['edit_form_submitted']:
        st.success("Entry updated successfully!")
        st.session_state['edit_form_submitted'] = False

def view_entries():
    """Advanced entry viewer with interactive table"""
    st.title("📖 Diary Entries")
    
    entries = load_entries()
    if not entries:
        st.info("No entries found. Start writing!")
        return
    
    # Convert to DataFrame for AgGrid
    df = pd.DataFrame(entries)
    df['date'] = pd.to_datetime(df['date'])
    
    # Ensure all required columns exist
    required_columns = ['date', 'title', 'mood', 'tags', 'word_count', 'sentiment']
    for col in required_columns:
        if col not in df.columns:
            if col == 'word_count':
                df[col] = df['content'].apply(lambda x: len(str(x).split()))
            elif col == 'sentiment':
                df[col] = 0.0  # Default sentiment value
            else:
                df[col] = ''  # Default empty value for other columns
    
    # Add selection for PDF download - single entry only
    st.subheader("Download Entry as PDF")
    selected_index = st.selectbox(
        "Select an entry to download",
        options=range(len(entries)),
        format_func=lambda x: f"{entries[x]['date']} - {entries[x]['title']}"
    )
    
    if st.button("📥 Generate PDF"):
        selected_entry = [entries[selected_index]]  # Create a list with just the selected entry
        with st.spinner("Generating PDF..."):
            pdf_path = generate_pdf(selected_entry)
            
            if pdf_path is None:
                st.error("Failed to generate PDF. Please try again.")
                return
                
            try:
                # Read the PDF file
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                
                # Create download button
                st.download_button(
                    label="Click to Download PDF",
                    data=pdf_bytes,
                    file_name=f"diary_entry_{entries[selected_index]['date']}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
                
                # Clean up the temporary file
                os.unlink(pdf_path)
            except Exception as e:
                st.error(f"Error processing PDF: {str(e)}")
                if pdf_path and os.path.exists(pdf_path):
                    try:
                        os.unlink(pdf_path)
                    except:
                        pass
    
    # Interactive table
    gb = GridOptionsBuilder.from_dataframe(df[required_columns])
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
    gb.configure_selection('single', use_checkbox=True)
    gb.configure_columns(['date'], type=["customDateTimeFormat"], custom_format_string='yyyy-MM-dd')
    gb.configure_columns(['sentiment'], type=["numericColumn"], precision=2)
    grid_options = gb.build()
    
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        height=400,
        width='100%',
        data_return_mode='FILTERED',
        update_mode='MODEL_CHANGED',
        fit_columns_on_grid_load=True,
        theme='streamlit'
    )
    
    # Get selected rows and ensure it's a list
    selected_rows = grid_response.get('selected_rows', [])
    if isinstance(selected_rows, pd.DataFrame):
        selected_rows = selected_rows.to_dict('records')
    
    # Show selected entry details
    if selected_rows and len(selected_rows) > 0:
        entry_id = selected_rows[0]['id']
        entry = next((e for e in entries if e['id'] == entry_id), None)
        
        if entry:
            st.subheader(entry['title'])
            st.write(f"**Date:** {entry['date']} | **Mood:** {entry['mood']}")
            st.write(f"**Tags:** {', '.join(entry['tags'])}")
            
            # Handle missing fields gracefully
            sentiment = entry.get('sentiment', 0.0)
            word_count = entry.get('word_count', len(entry['content'].split()))
            
            st.write(f"**Sentiment:** {sentiment:.2f} | **Words:** {word_count}")
            
            # Add edit button
            if st.button("✏️ Edit Entry"):
                st.session_state['editing_entry'] = entry
                st.rerun()
            
            st.markdown("---")
            # Display content with Markdown rendering
            st.markdown(entry['content'])
            
            if entry.get('image'):
                st.markdown("---")
                img_bytes = base64.b64decode(entry['image'])
                st.image(Image.open(io.BytesIO(img_bytes)), caption="Attached Image", width=400)
            
            st.markdown("---")
            
            # Initialize session state for delete confirmation
            if 'delete_confirmed' not in st.session_state:
                st.session_state['delete_confirmed'] = False
                
            if st.button("Delete Entry", key=f"delete_{entry['id']}"):
                st.session_state['delete_confirmed'] = True
                st.session_state['entry_to_delete'] = entry['id']
                st.rerun()
                
            # Show passkey verification if delete is confirmed
            if st.session_state.get('delete_confirmed', False) and st.session_state.get('entry_to_delete') == entry['id']:
                st.warning("🔒 Please enter the entry passkey to delete this entry")
                
                with st.form("delete_entry_form"):
                    passkey = st.text_input("Enter Entry Passkey", type="password")
                    submit = st.form_submit_button("Delete")
                    
                    if submit:
                        if hash_passkey(passkey) == entry['passkey_hash']:
                            entries = [e for e in entries if e['id'] != entry['id']]
                            save_entries(entries)
                            st.success("Entry deleted!")
                            
                            # Reset session state
                            st.session_state['delete_confirmed'] = False
                            st.session_state['entry_to_delete'] = None
                            st.session_state['passkey_verified'] = False
                            
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Incorrect passkey")

def show_stats():
    """Enhanced statistics dashboard"""
    st.title("📊 Diary Analytics")
    
    entries = load_entries()
    if not entries:
        st.info("No data to analyze yet")
        return
    
    df = pd.DataFrame(entries)
    df['date'] = pd.to_datetime(df['date'])
    
    # KPI Cards
    st.subheader("Writing Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Entries", len(df))
    with col2:
        st.metric("Total Words", df['word_count'].sum())
    with col3:
        st.metric("Avg. Sentiment", f"{df['sentiment'].mean():.2f}")
    with col4:
        st.metric("Avg. Words/Entry", f"{df['word_count'].mean():.0f}")
    
    # Mood Analysis
    st.markdown("---")
    st.subheader("Mood Analysis")
    
    tab1, tab2, tab3 = st.tabs(["Distribution", "Timeline", "Relationships"])
    
    with tab1:
        mood_counts = df['mood'].value_counts().reset_index()
        fig1 = px.pie(mood_counts, values='count', names='mood', 
                     title='Mood Distribution', hole=0.3)
        st.plotly_chart(fig1, use_container_width=True)
    
    with tab2:
        fig2 = mood_timeline(df)
        st.plotly_chart(fig2, use_container_width=True)
    
    with tab3:
        fig3 = px.scatter(df, x='word_count', y='sentiment', color='mood',
                         title='Word Count vs. Sentiment by Mood',
                         hover_data=['date', 'title'])
        st.plotly_chart(fig3, use_container_width=True)
    
    # Writing Habits
    st.markdown("---")
    st.subheader("Writing Habits")
    
    day_counts, hour_counts = analyze_writing_habits(df)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig4 = px.bar(day_counts, x='Day', y='Entries', 
                      title='Entries by Day of Week',
                      color='Entries', color_continuous_scale='Blues')
        st.plotly_chart(fig4, use_container_width=True)
    
    with col2:
        fig5 = px.bar(hour_counts, x='Hour', y='Entries',
                     title='Entries by Hour of Day',
                     color='Entries', color_continuous_scale='Greens')
        st.plotly_chart(fig5, use_container_width=True)
    
    # Content Analysis
    st.markdown("---")
    st.subheader("Content Analysis")
    
    all_text = " ".join(df['content'])
    
    if all_text.strip():
        tab1, tab2 = st.tabs(["Word Cloud", "Top Keywords"])
        
        with tab1:
            st.pyplot(create_wordcloud(all_text))
        
        with tab2:
            keywords = extract_keywords(all_text, 20)
            keywords_df = pd.DataFrame(keywords, columns=['Keyword', 'Count'])
            st.dataframe(keywords_df.sort_values('Count', ascending=False), 
                        height=400, use_container_width=True)
    else:
        st.info("Not enough text for content analysis")

# --- Main App ---
def main():
    st.sidebar.title("My Diary")
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3281/3281289.png", width=100)
    
    # Check if passkey is set up
    if not PASSKEY_FILE.exists():
        if not setup_passkey():
            return
    
    # Check if we need to redirect to view entries
    if 'redirect_to_view' in st.session_state and st.session_state['redirect_to_view']:
        del st.session_state['redirect_to_view']
        st.session_state['page'] = "View Entries"
    
    # Get the current page from session state or default to "Write Entry"
    current_page = st.session_state.get('page', "Write Entry")
    
    page = st.sidebar.radio(
        "Navigation",
        ["Write Entry", "View Entries", "Statistics"],
        index=0 if current_page == "Write Entry" else 1 if current_page == "View Entries" else 2,
        key="page_radio"
    )
    
    # Update session state with selected page
    st.session_state['page'] = page
    
    st.sidebar.markdown("---")
    st.sidebar.info("""
    **Advanced Diary Features:**
    - Encrypted storage
    - Sentiment analysis
    - Writing analytics
    - Image attachments
    - Markdown support
    - Edit entries
    - Passkey protection
    """)
    
    # Check if we're editing an entry
    if 'editing_entry' in st.session_state:
        edit_entry(st.session_state['editing_entry'])
        if st.button("Back to View Entries"):
            del st.session_state['editing_entry']
            st.rerun()
    else:
        if page == "Write Entry":
            write_entry()
        elif page == "View Entries":
            view_entries()
        elif page == "Statistics":
            show_stats()

if __name__ == "__main__":
    main()