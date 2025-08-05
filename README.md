# tyra
Tyra Flask Poc

#Command Line
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


    #Debug
    which python
    /Users/ankita/Documents/my_work/women_health_chatbot/venv/bin/python



#Srcapper
How to Use:
Save the Code: Save the code below as scrape_tribher_final.py.
Install Libraries: pip install requests beautifulsoup4
Run the Script: python scrape_tribher_final.py
Check the Output: A file named tribher_data_final.json will be created with the correctly structured data.



#Version Control
All the feature of *Tyra_future_feature_updated_28Jun* implemented in folder: FeatureFeature_Comp_4Jul_5_women_health_chatbot

#Gemini Rate Limit
https://ai.google.dev/gemini-api/docs/rate-limits#free-tier


#Test Users
7760968651    Rita    "Young Adulthood"
7760968652    Nisha   Prenatal
7760968653    Rose    Postnatal ratanpd@gmail.com
7760968654    Mery    Postnatal



#Pending Item

In a production system, this would be a database or a Redis cache

spike Control

convert json
log backpain not coming in dashboard
interaction log: key word for interaction

Download as PDF
Sharalable link: empty
json for other language => feature complete


standalone vs website embedding, app embedding
steps for production
fly vs render hosting

guest mode not aware of tribher


Cache LLM API responses persitently -The standard "next step" for a production application would be to integrate a dedicated caching server like Redis.


#Done
recreate all the json files based on english

implement a request queue in your Flask app to throttle excessive requests

Cache LLM API responses for common queries to reduce API calls and bandwidth - In memory caching

Guest Mode - Free chat (no login/signup) by default
    Option to chose login/sigup for customized response


predict ovulation and fertility windows

interaction_log
health_logs	not paased to AI to understand about user?

#Milestone:

Monolith Final: Feature_Comp_monolith_24Jul_5_women_health_chatbot/ (Jul 24)
Guest Mode: Feature_Comp_22Jul_1_women_health_chatbot/ (Jul 22)
Fertility: 21Jul_2_women_health_chatbot/


#Material
Health data
    https://www.healthyapps.dev/developers
    https://sahha.ai/pricing

#Language

                        <select name="language" id="language" required>
                            <option value="en" selected>English</option>
                            <option value="bn">বাংলা (Bengali)</option>
                            <option value="gu">ગુજરાતી (Gujarati)</option>
                            <option value="hi">हिन्दी (Hindi)</option>
                            <option value="kn">ಕನ್ನಡ (Kannada)</option>
                            <option value="ml">മലയാളം (Malayalam)</option>
                            <option value="mr">मराठी (Marathi)</option>
                            <option value="or">ଓଡ଼ିଆ (Odia)</option>
                            <option value="pa">ਪੰਜਾਬੀ (Punjabi)</option>
                            <option value="ta">தமிழ் (Tamil)</option>
                            <option value="te">తెలుగు (Telugu)</option>
                            <option value="ur">اردو (Urdu)</option>
                            <option value="ar">العربية (Arabic)</option>
                        </select>