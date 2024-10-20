import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from images import b64_images
import base64
from PIL import Image
import io
from io import BytesIO
import json
import unicodedata
import math
import requests
import re
from utility import check_password

# Do not continue if check_password is not True.  
if not check_password():  
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def get_completion(prompt, model="gpt-4o", temperature=0, top_p=1.0, max_tokens=256, n=1, json_output=False):
    if json_output == True:
      output_json_structure = {"type": "json_object"}
    else:
      output_json_structure = None

    messages = [{"role": "system", "content": "You are an automated image tagging robot. You MUST only rely solely on text found in the provided image when returning the 'text_in_image', do not rely on external information when generating this field."},{"role": "user", "content": prompt}]
    response = client.chat.completions.create( #originally was openai.chat.completions
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        n=1,
        response_format=output_json_structure,
    )
    return response.choices[0].message.content
    
# def encode_image(image_path):
#   with open(image_path, "rb") as image_file:
#     return base64.b64encode(image_file.read()).decode('utf-8')

def encode_image(image_obj):
    return base64.b64encode(image_obj).decode('utf-8')

def scroll_to(element_id):
    components.html(f'''
        <script>     
            async function close_sleep_scroll(ms){{
                try{{
                    window.parent.document.getElementsByTagName("summary")[1].click();}}
                catch{{
                    document.getElementsByTagName("summary")[1].click();}}
                await new Promise(r => setTimeout(r, ms));
                try{{
                    var element = window.parent.document.getElementById("{element_id}");}}
                catch{{
                    var element = document.getElementById("{element_id}");}}
                element.scrollIntoView({{behavior: 'smooth'}});                
            }}
            close_sleep_scroll(1000);
        </script>
    '''.encode(), height=0)

st.set_page_config(layout="wide")
st.markdown('<div style="text-align: right;"><i>v1.36</i></div>', unsafe_allow_html=True)
st.markdown(
    f""" 
        <style>
        .element-container:has(iframe[height="0"]) {{
          display: none;
        }}
        </style>
    """, unsafe_allow_html=True
)
st.title('🤖 Trade Mark Automatic Indexer') 

with st.expander("📌 **Getting Started**"):
    st.markdown('''👋 Greetings!
----------
**Background:**  
Every day IPOS receives hundreds of trade mark applications which contain images that need to be "indexed" or tagged with the relevant information about the textual and graphical elements they contain. This enables both customers and staff to quickly find information on trade marks filed using a simple keyword search (this is on top of the image-based search we also provide). Today, this is done manually by a team of indexing officers and this POC is an attempt to leverage AI to assist them with suggested indices.

**Instructions:**  
To use, simply upload an image to be indexed or select one from the list of samples we have prepared.  
Have fun indexing!
                                
To view the raw data from OpenAI, refer to '⚙️ 🧰 **Debugging**' after the indices have been generated, or leave us some feedback at '😀 **Feedback**' to help us do better.''')

col_top1, col_top2 = st.columns((1,2))

with col_top1:
    st.header('👉 A) Upload an image')
    uploaded_file = st.file_uploader("Upload your mark to generate suggested indices.", type=['png', 'jpg','gif'], accept_multiple_files=False, key=None, help=None, on_change=None, args=None, kwargs=None, disabled=False, label_visibility="visible")

selected_file=None
col_right=[]
rowN=0
with col_top2:
    st.header('or 👉 B) Select a sample image below')
    with st.expander('**Samples**'):
        n=0
        rowElements = []
        rows=math.ceil(len(b64_images)/6)
        for rowN in range(0,rows):
            rowElements.append(st.container())
            with rowElements[rowN]:
                col_right.append(st.columns((1,1,1,1,1,1)))
                for colN in range(0,6):
                    if n < len(b64_images):    
                        with col_right[rowN][n%6]:
                            #print(rowN,n%6)
                            if st.button(f'↓Sample {n+1}↓',type="primary"):
                                selected_file=BytesIO(base64.b64decode(b64_images[n]))
                                uploaded_file=None
                                scroll_to("preview")
                            st.image('data:image/jpg;base64,'+b64_images[n])
                            
                        n=n+1

col1, col2 = st.columns((1,1))

if uploaded_file or selected_file is not None:
    if uploaded_file is None:
        uploaded_file = selected_file
    # b64Str = encode_image(uploaded_file.read())
    # st.text(b64Str)
    # st.text(len(b64Str))

    # st.text(encode_image(uploaded_file))
    # imagefile = io.BytesIO(uploaded_file.read())
    with Image.open(uploaded_file) as im:
        width, height = im.size
        if width > 512 or height > 512:
            im.thumbnail((512, 512))
        img_byte_arr = io.BytesIO()
        background = Image.new("RGB", im.size, (255, 255, 255))
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        background.paste(im, mask=im)
        # im.convert('RGB').save(img_byte_arr, format='JPEG', quality=95)
        background.convert('L').save(img_byte_arr, format='JPEG', quality=100)
        # st.image(im)
        img_byte_arr = img_byte_arr.getvalue()
        b64Str=encode_image(img_byte_arr)
        # st.text(b64Str)
        # st.text(len(b64Str))
        image_data = base64.b64decode(b64Str)
        # Convert the decoded data to an image
        img = Image.open(BytesIO(image_data))
        with col1:
            st.header("🖼️ Image Preview",anchor="preview")
            st.image(img)

    with col2:
        st.header("🔍 Results: Indices Generated",anchor="results")
        with st.spinner('Generating indices...'):
            prompt=[
            {'type':'text',
                'text': "Your response should be a JSON object with 2 keys: 'description_of_devices','text_in_image'." 
                "'description_of_devices' should be a list of words or short phrases that describe each pictorial element in the image EXCLUDING any text or letters/alphabets/foreign characters and should not include words like 'logo', 'text', 'alphabets', 'letters', 'words', 'names' etc. If the image contains purely text and does not contain pictorial elements, this may be left empty."
                "'text_in_image' should be a list of ALL the TEXTUAL words/phrases present in the image including text in foreign chracters, e.g. Thai, Chinese, etc. This field should be left empty if there is no text in the image. Parts of text OF THE SAME LANGUAGE appearing together in the image should be output as a single string in the list, while text of different languages should be separated and returned as separate strings. Please ONLY provide responses solely based on what is found in the provided image."
                "E.g. Chinese characters and English words SHOULD NOT be returned as a single string, like '麻布茶房 Ice-Cream' should be returned as '麻布茶房' and 'Ice-Cream'."
                },
                {'type':'image_url',
                'image_url':{'url':f"data:image/jpeg;base64,{b64Str}"}
                }
            ]

            first_response = get_completion(prompt,model="gpt-4o",json_output=True)
            first_response_json=json.loads(first_response)
            text_in_image=list(dict.fromkeys(first_response_json['text_in_image']))
            description_of_devices=list(dict.fromkeys(first_response_json['description_of_devices']))
            second_response=''
            second_response_json={"english_words_coined_words_numbers_romanized_words":[],"chinese_words":[],"non-english_words_using_the_latin_alphabet":[],"non_chinese_foreign_words_not_in_latin_alphabet":[]}
            if len(text_in_image)>0:
                prompt=[
                {'type':'text',
                    'text': "Your response should be a JSON object with 4 keys: 'english_words_coined_words_numbers_romanized_words', 'chinese_words', 'non-english_words_using_the_latin_alphabet', 'non_chinese_foreign_words_not_in_latin_alphabet'."
                    "For each item in the provided list, classify it into one of the 4 keys. DO NOT split one item into multiple items."
                    "'english_words_coined_words_numbers_romanized_words' includes 1)English words, 2)words that do not belong to any language and have no known meaning, and 3) romanized foreign words (such as romanized japanese words like 'kawaii' and romanized korean words like 'daebak')."
                    "'non_chinese_foreign_words_not_in_latin_alphabet' MUST NOT contain any Chinese characters as they should be classified in 'chinese_words' instead, and MUST NOT contain any latin alphabets as they should be classified in either 'english_words_coined_words_numbers_romanized_words' or 'non-english_words_using_the_latin_alphabet'. This should contain words in other foreign characters such as Thai script, Japanese hiragana and katakana, korean script, indian brahmic scripts etc."
                    "'non-english_words_using_the_latin_alphabet' should only include words not in English but with a known meaning, but MUST NOT include romanised foreign words (e.g. it MUST NOT contain romanized japanese words like 'kawaii' and romanized korean words like 'daebak', EXCEPT names of places e.g. 'Hokkaido'). This should include words in languages that use the English alphabet such as Bahasa Melayu, German, French, Vietnamese, Swahili etc."
                    "List:"    
                    f"{text_in_image}"      
                    }
                ]

                second_response=get_completion(prompt,model="gpt-4o-mini",json_output=True)
                second_response_json=json.loads(second_response)

            third_response=''
            third_response_json={"translation":[],"transliteration":[]}
            transliteration_list=[]
            translation_list=[]
            if (len(second_response_json['chinese_words'])+len(second_response_json['non_chinese_foreign_words_not_in_latin_alphabet'])+len(second_response_json['non-english_words_using_the_latin_alphabet']))>0:
                inputList1=[','.join(x.replace(' ','')) for x in second_response_json['chinese_words']]+second_response_json['non_chinese_foreign_words_not_in_latin_alphabet']
                inputList2=second_response_json['chinese_words']+second_response_json['non_chinese_foreign_words_not_in_latin_alphabet']+second_response_json['non-english_words_using_the_latin_alphabet']
                prompt=[
                {'type':'text',
                    'text': "Your response should be a JSON object with 2 keys: 'transliteration' and 'translation', where the values in both keys are lists."
                    "For each string in the provided 'List1', provide a transliteration of the string in latin script in the key 'transliteration'. If the string contains commas, it should still be output as a single string in the key 'transliteration'."
                    "For each item in the provided 'List2', if the item has a meaning provide the meaning in English in the key 'translation', if it has no meaning then skip the item. DO NOT translate into non-English words and do not provide a romanized version of the foreign characters under 'translation'. For Chinese characters, provide the English meaning of the Chinese characters if they make sense."
                    "List1:"    
                    f"{inputList1}"
                    "List2:"    
                    f"{inputList2}"      
                    }
                ]
                third_response=get_completion(prompt,model="gpt-4o",json_output=True)
                third_response_json=json.loads(third_response)
                for item in third_response_json['transliteration']:
                    transliteration_list.append((unicodedata.normalize('NFD',item).encode('ASCII','ignore')).decode('ASCII'))
                for item in third_response_json['translation']:
                    translation_list.append((unicodedata.normalize('NFD',item).encode('ASCII','ignore')).decode('ASCII'))
                transliteration_list=list(dict.fromkeys(transliteration_list))
                translation_list=list(dict.fromkeys(translation_list))

    with col2:
        st.text_input("**Description of device**", value=('; ').join(first_response_json["description_of_devices"]))
        st.text_input("**English/coined words in mark**", value=('; ').join(second_response_json["english_words_coined_words_numbers_romanized_words"]))
        st.text_input("**Non-English words using the English alphabet**", value=('; ').join(second_response_json["non-english_words_using_the_latin_alphabet"]))
        st.text_input("**Chinese characters**", value=('; ').join(second_response_json["chinese_words"]))
        st.text_input("**Other foreign characters**", value=('; ').join(second_response_json["non_chinese_foreign_words_not_in_latin_alphabet"]))
        st.text_input("**Translation**", value=('; ').join(translation_list))
        st.text_input("**Transliteration**", value=re.sub(", *"," ",'; '.join(transliteration_list).lower()))

    with st.expander('⚙️ 🧰 **Debugging**'):
        
        colA, colB, colC = st.columns((1,1,1))
        with colA:
            st.markdown('**First response:**')
            st.text(first_response)
        with colB:
            st.markdown('**Second response:**')
            st.text(second_response)
        with colC:
            st.markdown('**Third response:**')
            st.text(third_response)
    
with st.expander('😀 **Feedback**',expanded=True):
    with st.form(key="feedback_form"):
        st.write("**Was this tool helpful?**")
        rating = st.feedback("thumbs")
        comments = st.text_input("**Why did you choose this rating? (optional)**")
        submit_form = st.form_submit_button(label="Submit", help="Click to submit your feedback")

        # Checking if all the fields are non-empty
        if submit_form:
            if rating==1 or rating==0:    
                URL = 'https://api.web3forms.com/submit'
                headers= {
                   "Content-Type": "application/json",
                   "Accept": "application/json",
                }
                payload = {
                   "access_key": st.secrets["WEB3FORMS_API_KEY"],
                   "message": str(rating)+";"+str(comments),
                }
                data = json.dumps(payload, separators=(',', ':'))
                session = requests.session()
                r = requests.post(URL, headers=headers, data=data)
                print(r.text)
                st.success("Form submitted, thank you for your feedback!")
            else:
                st.warning("Please indicate 👍 or 👎 before submitting the form.")