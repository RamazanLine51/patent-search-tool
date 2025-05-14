import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
import os
import json
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Patent Search Tool",
    page_icon="🔍",
    layout="wide",
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .patent-card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        background-color: #f8f9fa;
        border-left: 4px solid #4285F4;
    }
    .patent-title {
        color: #1a73e8;
        font-weight: bold;
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
    }
    .patent-info {
        font-size: 0.9rem;
        color: #5f6368;
        margin-bottom: 0.5rem;
    }
    .patent-abstract {
        font-size: 1rem;
        margin-top: 1rem;
    }
    .highlight {
        background-color: #e6f4ea;
        padding: 0.2rem;
        border-radius: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'saved_patents' not in st.session_state:
    st.session_state.saved_patents = []
if 'last_search_results' not in st.session_state:
    st.session_state.last_search_results = []

# Function to create Google Patents search URL
def create_search_url(company, keywords, num_results=25):
    base_url = "https://patents.google.com/patents/search"
    
    # Format the query to search for patents from the specific company with the keywords
    company_query = f'assignee:"{company}"'
    keyword_query = ' '.join([f'"{kw}"' for kw in keywords.split(',')])
    
    # Combine queries
    query = f"{company_query} {keyword_query}"
    
    # Encode the query for URL
    params = {
        'q': query,
        'num': num_results
    }
    
    # Construct the URL with parameters
    response = requests.get(base_url, params=params)
    return response.url

# Function to perform the web scraping
def scrape_google_patents(search_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(search_url, headers=headers)
        if response.status_code != 200:
            return None, f"Error: Status code {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract search results
        results = []
        search_results = soup.select('.search-result-item')
        
        if not search_results:
            return None, "No search results found or page structure may have changed."
        
        for result in search_results:
            try:
                # Extract title
                title_elem = result.select_one('.patent-title')
                title = title_elem.text.strip() if title_elem else "No title available"
                
                # Extract patent number/ID
                patent_id_elem = result.select_one('.patent-number')
                patent_id = patent_id_elem.text.strip() if patent_id_elem else "No ID available"
                
                # Extract link
                link_elem = result.select_one('a')
                link = "https://patents.google.com" + link_elem['href'] if link_elem and 'href' in link_elem.attrs else "#"
                
                # Extract filing date and other info
                filing_date = "Not available"
                assignee = "Not available"
                inventors = "Not available"
                
                info_elems = result.select('.patent-meta-data .patent-data')
                for elem in info_elems:
                    text = elem.text.strip()
                    if "Filing date" in text:
                        filing_date = text.replace("Filing date:", "").strip()
                    elif "Assignee" in text:
                        assignee = text.replace("Assignee:", "").strip()
                    elif "Inventor" in text:
                        inventors = text.replace("Inventor:", "").strip()
                
                # Extract abstract/description
                abstract_elem = result.select_one('.patent-abstract')
                abstract = abstract_elem.text.strip() if abstract_elem else "No abstract available"
                
                results.append({
                    'title': title,
                    'patent_id': patent_id,
                    'link': link,
                    'filing_date': filing_date,
                    'assignee': assignee,
                    'inventors': inventors,
                    'abstract': abstract
                })
                
            except Exception as e:
                st.error(f"Error parsing result: {str(e)}")
                continue
        
        return results, None
    
    except Exception as e:
        return None, f"Error during scraping: {str(e)}"

# Function to save patents to a file
def save_patents_to_file():
    if st.session_state.saved_patents:
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"saved_patents_{timestamp}.json"
        
        # Create a data directory if it doesn't exist
        if not os.path.exists("data"):
            os.makedirs("data")
        
        # Save the patents to a JSON file
        with open(f"data/{filename}", "w") as f:
            json.dump(st.session_state.saved_patents, f, indent=4)
        
        return filename
    return None

# Function to load saved patents from a file
def load_patents_from_file(file):
    try:
        file_content = file.read()
        patents = json.loads(file_content)
        return patents
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return []

# Sidebar for search parameters
st.sidebar.title("Search Parameters")

# Company selection
company_options = ["Apple", "Google", "Alphabet", "Microsoft", "Meta", "Amazon", "Samsung", "Other"]
selected_company = st.sidebar.selectbox("Select Company", company_options)

if selected_company == "Other":
    selected_company = st.sidebar.text_input("Enter Company Name")

# Keywords input
keywords = st.sidebar.text_area("Enter Keywords (comma separated)", 
                               "app store, search algorithm, ranking, recommendation system")

# Number of results
num_results = st.sidebar.slider("Number of Results", min_value=10, max_value=100, value=25, step=5)

# Search button
search_button = st.sidebar.button("Search Patents")

# History section in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Search History")

# Display search history
if st.session_state.search_history:
    for i, search in enumerate(st.session_state.search_history[-10:]):  # Show last 10 searches
        if st.sidebar.button(f"{search['company']} - {search['keywords'][:20]}...", key=f"history_{i}"):
            # Re-run the search with these parameters
            search_url = create_search_url(search['company'], search['keywords'], search['num_results'])
            with st.spinner('Searching patents...'):
                results, error = scrape_google_patents(search_url)
                if error:
                    st.error(error)
                else:
                    st.session_state.last_search_results = results
else:
    st.sidebar.write("No search history yet.")

# Saved patents section in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Saved Patents")

# Download saved patents button
if st.session_state.saved_patents:
    if st.sidebar.button("Download Saved Patents"):
        filename = save_patents_to_file()
        if filename:
            st.sidebar.success(f"Patents saved to {filename}")
    
    st.sidebar.write(f"{len(st.session_state.saved_patents)} patents saved")
else:
    st.sidebar.write("No patents saved yet.")

# Upload saved patents
st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("Upload Saved Patents", type=["json"])
if uploaded_file is not None:
    imported_patents = load_patents_from_file(uploaded_file)
    if imported_patents:
        # Add only new patents (avoid duplicates)
        existing_ids = [p['patent_id'] for p in st.session_state.saved_patents]
        new_patents = [p for p in imported_patents if p['patent_id'] not in existing_ids]
        
        if new_patents:
            st.session_state.saved_patents.extend(new_patents)
            st.sidebar.success(f"Imported {len(new_patents)} new patents.")
        else:
            st.sidebar.info("No new patents to import.")

# Main content area
st.title("Patent Search Tool 🔍")
st.markdown("Search for patents related to app store search algorithms from major tech companies.")

# Execute search when button is clicked
if search_button:
    if not selected_company or not keywords:
        st.warning("Please enter both a company name and keywords.")
    else:
        # Create search URL
        search_url = create_search_url(selected_company, keywords, num_results)
        
        # Add to search history
        st.session_state.search_history.append({
            'company': selected_company,
            'keywords': keywords,
            'num_results': num_results,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Display loading spinner
        with st.spinner('Searching patents...'):
            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))
            
            # Perform the scraping
            results, error = scrape_google_patents(search_url)
            
            if error:
                st.error(error)
            else:
                st.session_state.last_search_results = results

# Display search results
if st.session_state.last_search_results:
    st.subheader(f"Found {len(st.session_state.last_search_results)} Patents")
    
    # Add filters
    col1, col2 = st.columns(2)
    with col1:
        filter_text = st.text_input("Filter results by keyword")
    with col2:
        sort_option = st.selectbox("Sort by", ["Relevance", "Filing Date (Newest)", "Filing Date (Oldest)"])
    
    # Filter and sort results
    filtered_results = st.session_state.last_search_results
    if filter_text:
        filtered_results = [r for r in filtered_results if 
                          filter_text.lower() in r['title'].lower() or 
                          filter_text.lower() in r['abstract'].lower()]
    
    # Sort results
    if sort_option == "Filing Date (Newest)":
        # Try to parse dates, fallback to original order if not possible
        try:
            filtered_results = sorted(filtered_results, 
                                     key=lambda x: datetime.strptime(x['filing_date'], "%b %d, %Y") if x['filing_date'] != "Not available" else datetime(1900, 1, 1), 
                                     reverse=True)
        except:
            st.warning("Could not sort by date due to format inconsistencies.")
            
    elif sort_option == "Filing Date (Oldest)":
        try:
            filtered_results = sorted(filtered_results, 
                                     key=lambda x: datetime.strptime(x['filing_date'], "%b %d, %Y") if x['filing_date'] != "Not available" else datetime(2100, 1, 1))
        except:
            st.warning("Could not sort by date due to format inconsistencies.")
    
    # Display results
    for i, result in enumerate(filtered_results):
        col1, col2 = st.columns([0.9, 0.1])
        
        with col1:
            st.markdown(f"""
            <div class="patent-card">
                <div class="patent-title">{result['title']}</div>
                <div class="patent-info">
                    <strong>Patent ID:</strong> {result['patent_id']} | 
                    <strong>Filing Date:</strong> {result['filing_date']} | 
                    <strong>Assignee:</strong> {result['assignee']}
                </div>
                <div class="patent-info">
                    <strong>Inventors:</strong> {result['inventors']}
                </div>
                <div class="patent-abstract">{result['abstract'][:300]}...</div>
                <a href="{result['link']}" target="_blank">View Patent</a>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Check if this patent is already saved
            is_saved = any(p['patent_id'] == result['patent_id'] for p in st.session_state.saved_patents)
            
            if is_saved:
                if st.button("Unsave", key=f"unsave_{i}"):
                    # Remove from saved patents
                    st.session_state.saved_patents = [p for p in st.session_state.saved_patents if p['patent_id'] != result['patent_id']]
                    st.experimental_rerun()
            else:
                if st.button("Save", key=f"save_{i}"):
                    # Add to saved patents
                    st.session_state.saved_patents.append(result)
                    st.experimental_rerun()

# Display saved patents if no search results are being shown
elif 'saved_patents' in st.session_state and st.session_state.saved_patents and not st.session_state.last_search_results:
    st.subheader("Your Saved Patents")
    
    for i, result in enumerate(st.session_state.saved_patents):
        col1, col2 = st.columns([0.9, 0.1])
        
        with col1:
            st.markdown(f"""
            <div class="patent-card">
                <div class="patent-title">{result['title']}</div>
                <div class="patent-info">
                    <strong>Patent ID:</strong> {result['patent_id']} | 
                    <strong>Filing Date:</strong> {result['filing_date']} | 
                    <strong>Assignee:</strong> {result['assignee']}
                </div>
                <div class="patent-info">
                    <strong>Inventors:</strong> {result['inventors']}
                </div>
                <div class="patent-abstract">{result['abstract'][:300]}...</div>
                <a href="{result['link']}" target="_blank">View Patent</a>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("Remove", key=f"remove_{i}"):
                # Remove from saved patents
                st.session_state.saved_patents.remove(result)
                st.experimental_rerun()
else:
    st.info("Use the search form in the sidebar to find patents related to app store search algorithms.")
    
# Footer
st.markdown("---")
st.markdown("*Patent Search Tool - Built with Streamlit*")
