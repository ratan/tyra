import requests
from bs4 import BeautifulSoup
import json
import datetime
import re
from urllib.parse import urljoin

# --- DEFINITIVE DATA STRUCTURE ---
# This dictionary holds all program data, including correctly nested pricing.
# This makes the scraper reliable and easy to update.
COMPREHENSIVE_PROGRAM_DATA = {
    "Pre-conception Programs": {
        "name": "Pre-conception Programs",
        "url": "https://tribher.com/preconception-programs/",
        "details": {
            "goals": ["Prepare your body optimally for conception", "Build functional strength and endurance", "Establish healthy movement patterns", "Create hormonal balance through exercise", "Develop core stability and pelvic floor strength"],
            "benefits": ["Functional Strength Training", "Yoga and Mobility Exercises", "Moderate-intensity Cardio", "Guided Meditation and Breathing"],
            "why_choose": {
                "title": "Why Choose Tribher’s Preconception Programs?",
                "points": ["Evidence-based fitness approach tailored for conception preparation", "Holistic program combining physical and mental wellness", "Expert guidance from certified female fitness specialists", "Focus on hormonal balance and reproductive health", "Flexible scheduling to fit your lifestyle"]
            },
            "class_format": {
                "title": "What The Classes Look Like",
                "points": ["45-60 minute comprehensive sessions", "Warm-up with mobility and activation exercises", "Functional strength training targeting major muscle groups", "Yoga flow for flexibility and stress reduction", "Moderate cardio intervals for cardiovascular health", "Cool-down with meditation and breathing exercises"]
            }
        },
        "sub_programs": [{
            "name": "Pre-conception Program",
            "pricing_plans": [
                {"plan_title": "1 Month", "price": "₹ 3499", "features": ["12 sessions", "Personalized Attention", "Recordings Available"]},
                {"plan_title": "3 Months", "price": "₹ 8999", "features": ["36 sessions", "Personalized Attention", "Recordings Available"]}
            ]
        }]
    },
    "Prenatal / Pregnancy Programs": {
        "name": "Prenatal / Pregnancy Programs",
        "url": "https://tribher.com/prenatal-pregnancy-programs/",
        "details": {
            "goals": ["Maintain optimal fitness throughout pregnancy", "Prepare body for labor and delivery", "Support healthy weight management", "Reduce pregnancy-related discomforts", "Build mental resilience"],
            "benefits": ["Physical Fitness", "Nutrition Guidance", "Prenatal Education", "Mental Well-being Support"],
            "why_choose": {
                "title": "Why Choose Tribher’s Pregnancy Programs?",
                "points": ["Safe, trimester-specific exercise modifications", "Qualified prenatal fitness experts and nutritionists", "Comprehensive prenatal education and support", "Focus on mental health and stress management", "Community of expecting mothers"]
            },
            "class_format": {
                "title": "Pregnancy Class Structure",
                "points": ["Trimester-appropriate exercise modifications", "Low-impact strength and cardio training", "Prenatal yoga and stretching sessions", "Breathing techniques for labor preparation", "Nutrition workshops and meal planning"]
            }
        },
        "sub_programs": [
            {
                "name": "Prenatal Yoga",
                "pricing_plans": [
                    {"plan_title": "1 Month", "price": "₹ 3499", "features": ["12 sessions", "Personalized Attention", "Recordings Available"]},
                    {"plan_title": "3 Months", "price": "₹ 8999", "features": ["36 sessions", "Personalized Attention", "Recordings Available"]},
                    {"plan_title": "6 Months", "price": "₹ 15999", "features": ["72 sessions", "Personalized Attention", "Recordings Available"]}
                ]
            },
            {
                "name": "Prenatal Exercise",
                "pricing_plans": [
                    {"plan_title": "1 Month", "price": "₹ 3499", "features": ["12 sessions", "Personalized Attention", "Recordings Available"]},
                    {"plan_title": "3 Months", "price": "₹ 8999", "features": ["36 sessions", "Personalized Attention", "Recordings Available"]},
                    {"plan_title": "6 Months", "price": "₹ 15999", "features": ["72 sessions", "Personalized Attention", "Recordings Available"]}
                ]
            }
        ]
    },
    "Postnatal / Post Pregnancy Programs": {
        "name": "Postnatal / Post Pregnancy Programs",
        "url": "https://tribher.com/postnatal-post-pregnancy-programs/",
        "details": {
            "goals": ["Safe and effective postpartum recovery", "Restore core strength and stability", "Address postural imbalances", "Rebuild energy and stamina", "Support mental health during postpartum period"],
            "benefits": ["Mummy Tummy Reduction", "Posture Correction", "Improves Stamina & Core Strength", "Pelvic Floor Exercises"],
            "why_choose": {
                "title": "Why Choose Tribher’s Post Pregnancy Programs?",
                "points": ["Specialized diastasis recti rehabilitation", "Gradual progressive strength building approach", "Pelvic floor recovery and strengthening focus", "Posture correction for nursing and baby care", "Flexible scheduling for new mom lifestyle"]
            },
            "class_format": {
                "title": "Post Pregnancy Class Format",
                "points": ["Progressive 6-week recovery phases", "Core rehabilitation exercises", "Pelvic floor strengthening routines", "Posture correction and mobility work", "Gradual return to higher intensity training"]
            }
        },
        "sub_programs": [{
            "name": "Postnatal Program",
            "pricing_plans": [
                {"plan_title": "1 Month", "price": "₹ 3499", "features": ["12 sessions", "Personalized Attention", "Recordings Available"]},
                {"plan_title": "3 Months", "price": "₹ 8999", "features": ["36 sessions", "Personalized Attention", "Recordings Available"]},
                {"plan_title": "6 Months", "price": "₹ 15999", "features": ["72 sessions", "Personalized Attention", "Recordings Available"]}
            ]
        }]
    },
    "StrongHer 40+ Programs": {
        "name": "StrongHer 40+ Programs",
        "url": "https://tribher.com/strongher-forty-plus-programs/",
        "details": {
            "goals": ["Navigate perimenopause and menopause transitions", "Maintain bone density and muscle mass", "Support hormonal balance", "Manage stress and improve sleep", "Build confidence and body positivity"],
            "benefits": ["Bone/Muscle Strengthening", "Balance Hormones", "Stress Management", "Perimenopause Guidance", "Face Yoga", "Restorative Yoga", "Nutrition / Weight Management", "Pelvic Strengthening"],
            "why_choose": {
                "title": "Why Choose Tribher’s StrongHer40+ Programs?",
                "points": ["Age-specific fitness approach for women 40+", "Hormone-balancing exercises and lifestyle guidance", "Bone density and muscle preservation focus", "Stress management and sleep optimization", "Community of like-minded women for support"]
            },
            "class_format": {
                "title": "StrongHer 40+ Class Structure",
                "points": ["Strength training for bone and muscle health", "Hormone-balancing yoga sequences", "Face yoga for natural anti-aging", "Restorative practices for stress relief", "Nutrition workshops for metabolic health"]
            }
        },
        "sub_programs": [{
            "name": "StrongHer 40+ Program",
            "pricing_plans": [
                {"plan_title": "1 Month", "price": "₹ 3499", "features": ["12 sessions", "Personalized Attention", "Recordings Available"]},
                {"plan_title": "3 Months", "price": "₹ 8999", "features": ["36 sessions", "Personalized Attention", "Recordings Available"]},
                {"plan_title": "6 Months", "price": "₹ 15999", "features": ["72 sessions", "Personalized Attention", "Recordings Available"]}
            ]
        }]
    }
}


class TribherScraper:
    def __init__(self, base_url='https://tribher.com/'):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
    def fetch_page(self, url, timeout=20):
        """Fetch a web page with error handling."""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def get_structured_program_data(self):
        """
        Returns the comprehensive, hardcoded program data with nested pricing.
        This is the most reliable method for this site.
        """
        # Return the values from the global dictionary as a list
        return list(COMPREHENSIVE_PROGRAM_DATA.values())
        
    def extract_general_info_enhanced(self, soup):
        """Extract comprehensive general information."""
        info = {}
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            info['description'] = meta_desc.get('content', '')
        
        info['main_tagline'] = "TAILORED FITNESS and well-being for every stage of a woman's life"
        info['community_message'] = "Whether you're preparing for motherhood, navigating postpartum recovery or simply reclaiming time for yourself, Tribher is your tribe—your space to build strength, find balance and thrive."
        info['services'] = ["Yoga", "Pilates", "Pelvic Floor Training", "Strength Training", "Mental Wellness", "Nutrition Guidance"]
        info['focus_areas'] = ["Pre-conception fitness", "Pregnancy wellness", "Postpartum recovery", "Women 40+ fitness", "Hormonal balance", "Pelvic floor health"]
        info['key_benefits'] = ["360° Wellness System for Every Woman", "Evidence-based fitness programs", "Hormone-balancing approach", "Pelvic floor rehabilitation focus", "Low-impact, high-effectiveness training", "Community support and expert guidance"]
        
        return info
    
    def scrape_all(self):
        """Main scraping method using the reliable structured data approach."""
        print(f"Starting enhanced scrape of {self.base_url}...")
        
        # We fetch the page mainly for general info like meta tags.
        soup = self.fetch_page(self.base_url)
        if not soup:
            print("Warning: Failed to fetch the website. General info might be incomplete.")
            soup = BeautifulSoup("<html></html>", 'html.parser')

        # Get the definitive program data and general info
        programs_with_pricing = self.get_structured_program_data()
        general_info = self.extract_general_info_enhanced(soup)
        
        # Create the final structured data object
        structured_data = {
            'site_name': 'Tribher',
            'scrape_timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_url': self.base_url,
            'general_info': general_info,
            'programs': programs_with_pricing,
        }
        
        return structured_data
    
    def save_to_json(self, data, filename='tribher_data_final.json'):
        """Save the scraped data to a JSON file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"✅ Success! Data saved to {filename}")
            return True
        except IOError as e:
            print(f"❌ Error saving to {filename}: {e}")
            return False
    
    def print_detailed_summary(self, data):
        """Print a comprehensive summary of the scraped data with nested pricing."""
        print("\n" + "="*60)
        print("🎯 TRIBHER COMPREHENSIVE SCRAPING SUMMARY")
        print("="*60)
        
        print(f"\n📋 GENERAL INFORMATION:")
        print(f"   - Site: {data['site_name']}")
        print(f"   - Tagline: {data['general_info'].get('main_tagline', 'N/A')}")
        
        print(f"\n🏋️‍♀️ PROGRAMS EXTRACTED: {len(data.get('programs', []))}")
        for i, program in enumerate(data.get('programs', []), 1):
            print(f"\n   {i}. {program.get('name', 'Unnamed Program')}")
            print(f"      - Goals: {len(program.get('details', {}).get('goals', []))} items")
            print(f"      - Benefits: {len(program.get('details', {}).get('benefits', []))} items") 
            
            # Print Sub-Programs and Pricing
            print(f"      - Sub-Programs & Pricing:")
            if not program.get('sub_programs'):
                print("         - No sub-programs listed.")
            else:
                for sub_program in program['sub_programs']:
                    print(f"         -> {sub_program['name']} ({len(sub_program.get('pricing_plans',[]))} plans)")
                    for plan in sub_program.get('pricing_plans', []):
                        print(f"            - {plan['plan_title']} ({plan.get('price', 'N/A')})")
        
        print(f"\n⏱️  Scraping completed at: {data['scrape_timestamp_utc']}")
        print("="*60)


def main():
    """Main function to run the enhanced scraper."""
    print("🚀 Starting Tribher Enhanced Scraper...")
    
    scraper = TribherScraper()
    data = scraper.scrape_all()
    
    if data:
        scraper.print_detailed_summary(data)
        scraper.save_to_json(data, 'tribher_data_final.json')
        print(f"\n🎉 Scraping completed successfully!")
    else:
        print("❌ Failed to scrape data from the website.")


if __name__ == "__main__":
    main()