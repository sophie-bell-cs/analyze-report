import matplotlib.pyplot as plt
from collections import defaultdict
import re
import csv
import streamlit as st
from PyPDF2 import PdfReader
from PyPDF2.errors import DependencyError
import io

interest_words_file = open('words_of_interest.txt', 'r')
interest_words_lines = interest_words_file.readlines()
interest_words = {}
for line in interest_words_lines:
    words = [word.strip() for word in line.split(',')]
    interest_words[words[0]] = words[1:]
interest_words_file.close()

#dictionary of single word terms that are also present in multi-word terms
partials = {'sustainab*': ['sustainable material*'], 'nutrient*': ['>nutrient loading'], 'waste': ['>waste water', '>zero waste'], 'charger*': ['>super charger*']}
#dictionary of terms that could be used to define acronyms
acronyms = {'greenhouse': ['ghg'], 'climat*': ['unfccc', 'ipcc', 'ogci'], '>carbon capture': ['ccs', 'ccus'], 'fluorocarbon*': ['hfc', 'cfc']}

st.title("Analyze Files for Planetary Boundary Framework Sentiment")
uploaded_files = st.file_uploader("Upload pdf files", type=['pdf'], accept_multiple_files=True)

def process_text(text, report_info):
    # normalize text
    text = text.lower()
    text = re.sub(r'\n', ' ', text).strip()
    text_items = text.split()

    #counts total amount of text items if they're not numbers (total word count)
    file_total = len([item for item in text_items if not item.isdigit()])

    word_hits = []
    #initializes a dictionary with each Planetary Boundary category as the key
    category_count = {category: 0 for category in interest_words.keys()}
    # initializes category map for locations of each word in the categories
    category_map = {}

    #iterates through each word and category in the word list
    for key, items in interest_words.items():
        #iterates through each word in the word list
        for hit in items:
            if '*' in hit and '>' not in hit:
                # terms are marked with '*' if we want to search for different prefixes and suffixes
                # terms are marked with '>' if they contain multiple words, this code segment only applies to single-word terms
                root = re.escape(hit[:-1]) # removes '*' marker
                pattern = rf'\b\w*{root}\w*\b' # assigns regex pattern to accept words with different beginning and endings

            elif '>' in hit:
                terms = hit.split(' ') #creates a list of the words in a multi-word term
                patterns = [] #creates list of patterns specific to each word in the term
                for term in terms:
                    if '>' in term:
                        position_pattern = re.escape(term[1:]) # removes '>' marker
                    elif '*' in term:
                        root = re.escape(term[:-1]) # removes '*' marker
                        position_pattern = rf'\b\w*{root}\w*\b' #assigns regex pattern to accept word in the term that could have different prefixes & suffixes
                    else:
                        position_pattern = rf'\b{re.escape(term)}\b' # if no marker for the word, will only count exact matches
                    patterns.append(position_pattern)
                if len(patterns) == 2:
                    pattern = rf"{patterns[0]}(?:\W{{0,4}})\s*{patterns[1]}" # regex pattern for 2-word terms, will count as match if the words are within 4 characters of each other to account for spaces/dashes/articles
                elif len(patterns) == 3:
                    pattern = rf"{patterns[0]}(?:\W{{0,4}})\s*{patterns[1]}(?:\W{{0,4}})\s*{patterns[2]}" #regex pattern for 3-word terms will count as match if words are within 4 characters of each other
            else:
                pattern = rf'\b{re.escape(hit)}\b' # if no marker for the term, will only count exact matches

            #creates iterable list with matches found in the text from the regex patterns
            finds = re.finditer(pattern, text)

            # for each match, appends the original item from the wordlist, the word that matched it in the text, and the start and end index of it in the text
            for find in finds:
                word_hits.append([hit, find.group(), find.span()])
                category_count[key] += 1 #updates category count
                category_map[find.group()] = key #updates category map
    double = []
    word_hits.sort(key=lambda x: x[2][0]) # sorts matches by their location in the text
    counted = []

    #iterates through the matches, noting the match that occured before and after them
    for i in range(len(word_hits) - 1):
        prev_word, _, _ = word_hits[i-1]
        curr_word, _, _ = word_hits[i]
        next_word, _, _ = word_hits[i + 1]

        #iterates through the dictionary of one word terms that are also present in multiple word terms
        for part, fulls in partials.items():
            # if the current match in the iteration is a multiple word term and the match before or after it is a corresponding single word term, appends it to a list of double-counts
            if curr_word in fulls:
                if next_word == part:
                    double.append(word_hits[i+1])
                elif prev_word == part:
                    double.append(word_hits[i-1])

        # iterates through the dictionary of terms that are also present in acronyms
        for acronym_part, acronym in acronyms.items():
           # if the current match in the iteration is an acronym and the match before or after it is a corresponding term, appends it to a list of double-counts
           if curr_word in acronym and curr_word not in counted:
               if next_word == acronym_part:
                   double.append(word_hits[i + 1])
               elif prev_word == acronym_part:
                   double.append(word_hits[i - 1])

    #iterates through list of double-counted terms
    for nonCount in double:
        if nonCount in word_hits:
            word_hits.remove(nonCount) # if the term is still in the matched word list, removes it
            # updates category count and map
            category = category_map.get(nonCount[0])
            if category and category_count[category] > 0:
                category_count[category] -= 1
    #print(f'Double Counted: {double}')

    #calculates frequency of terms for each category
    category_frequency = {category: (count / file_total * 100) for category, count in category_count.items()}

    return report_info, category_frequency, file_total, len(word_hits)

graph_info = []
csv_info = []

if uploaded_files:
    st.header('Add information for each file.')
    st.divider()
    for file in uploaded_files:
        try:
            file_bytes = PdfReader(io.BytesIO(file.read()))
            if pdf_reader.is_encrypted:
                st.warning(f"{file.name} is encrypted and will be skipped.")
                continue

            st.subheader(file.name)

            with st.form(key=f"form_{file.name}"):
                yr_comp_rep = st.text_input("Enter Year, Company, Report Type (comma separated): ", key=f"report_{file.name}")
                submit_button = st.form_submit_button(label='Submit Info')
                elmnts = [e.strip() for e in yr_comp_rep.split(',')]
                if submit_button and len(elmnts) == 3:
                    if len(elmnts) == 3:
                        st.write(f'Year: {elmnts[0]}')
                        st.write(f'Company: {elmnts[1]}')
                        st.write(f'Report Type: {elmnts[2]}')

                        pdf_reader = PdfReader(file_bytes)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text() or ""

                        result = process_text(text, elmnts)
                        graph_result = [result[0][0], result[0][1], result[0][2], result[1]]
                        csv_result = graph_result + [result[2], result[3]]
                        graph_info.append(graph_result)
                        csv_info.append(csv_result)

        except DependencyError:
            continue
        except Exception as e:
            continue

if graph_info:

    graph_info.sort(key=lambda x: x[2])

    categories = list(graph_info[0][3].keys())
    category_colors = plt.cm.tab10.colors

    fig, ax = plt.subplots(figsize=(12, 6))

    bar_width = 0.2
    bar_gap = 0.02
    company_spacing = 0.5

    company_data = defaultdict(list)
    for company, report_type, year, freq in graph_info:
        company_data[company].append((year, report_type, freq))

    x_positions = []
    tick_labels = []

    current_x = 0
    for company, reports in company_data.items():

        reports.sort(key=lambda x: x[0])
        for year, report_type, freq in reports:
            x_positions.append(current_x)

            bottom = 0
            for cat_idx, category in enumerate(categories):
                height = freq.get(category, 0)
                ax.bar(current_x, height, bottom=bottom, width=bar_width,
                       color=category_colors[cat_idx % len(category_colors)])
                bottom += height

            tick_labels.append(f"{company}, {year}, {report_type}")

            current_x += bar_width + bar_gap

        current_x += company_spacing

    ax.set_xticks(x_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha="right")
    ax.set_xlabel("Report")
    ax.set_ylabel("Frequency (%)")
    ax.set_title("Planetary Boundary Framework Word Frequency by Category")
    ax.legend(categories, title="Categories", bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.tight_layout()
    st.pyplot(fig)

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)

    st.download_button(
        label="Download Graph",
        data=buf.getvalue(),
        file_name="pb_wordcount_graph.png",
        mime="image/png"
    )

if csv_info:
    categories = list(graph_info[0][3].keys())
    csv_headers = ['Company', 'Report', 'Year', 'Total Word Count'] + categories + ['Total Hit Count', 'Total Frequency']
    csv_rows = []

    for company, report, year, category_dict, Wcount, Hcount in csv_info:
        row = [company, report, year, Wcount]
        for category in categories:
            row.append(category_dict.get(category, 0))

        total_freq = Hcount / Wcount if Wcount > 0 else 0
        row.extend([Hcount, total_freq])
        csv_rows.append(row)


    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(csv_headers)
    writer.writerows(csv_rows)

    st.download_button(
        label="Download CSV",
        data=output.getvalue(),
        file_name="pb_wordcount_analysis.csv",
        mime="text/csv"
    )

