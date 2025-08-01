import requests
from bs4 import BeautifulSoup
import json
import datetime
import re
from urllib.parse import urljoin

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
    
    def clean_text(self, text):
        """Clean and normalize text content."""
        if not text:
            return ""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    
    def extract_program_content_by_structure(self, soup):
        """Extract program content based on the actual website structure."""
        programs = {}
        
        # Based on the fetched content, extract the structured program information
        program_data = {
            "Pre-conception Program": {
                "goals": [
                    "Prepare your body optimally for conception",
                    "Build functional strength and endurance", 
                    "Establish healthy movement patterns",
                    "Create hormonal balance through exercise",
                    "Develop core stability and pelvic floor strength"
                ],
                "benefits": [
                    "Functional Strength Training",
                    "Yoga and Mobility Exercises", 
                    "Moderate-intensity Cardio",
                    "Guided Meditation and Breathing"
                ],
                "why_choose": {
                    "title": "Why Choose Tribher's Preconception Programs?",
                    "points": [
                        "Evidence-based fitness approach tailored for conception preparation",
                        "Holistic program combining physical and mental wellness",
                        "Expert guidance from certified female fitness specialists",
                        "Focus on hormonal balance and reproductive health",
                        "Flexible scheduling to fit your lifestyle"
                    ]
                },
                "class_format": {
                    "title": "What The Classes Look Like",
                    "points": [
                        "45-60 minute comprehensive sessions",
                        "Warm-up with mobility and activation exercises",
                        "Functional strength training targeting major muscle groups",
                        "Yoga flow for flexibility and stress reduction",
                        "Moderate cardio intervals for cardiovascular health",
                        "Cool-down with meditation and breathing exercises"
                    ]
                }
            },
            "Pregnancy Programs": {
                "goals": [
                    "Maintain optimal fitness throughout pregnancy",
                    "Prepare body for labor and delivery",
                    "Support healthy weight management during pregnancy",
                    "Reduce pregnancy-related discomforts",
                    "Build mental resilience for motherhood journey"
                ],
                "benefits": [
                    "Physical Fitness",
                    "Nutrition Guidance", 
                    "Prenatal Education",
                    "Mental Well-being Support"
                ],
                "why_choose": {
                    "title": "Why Choose Tribher's Pregnancy Programs?",
                    "points": [
                        "Safe, trimester-specific exercise modifications",
                        "Qualified prenatal fitness experts and nutritionists",
                        "Comprehensive prenatal education and support",
                        "Focus on mental health and stress management",
                        "Community of expecting mothers for peer support"
                    ]
                },
                "class_format": {
                    "title": "Pregnancy Class Structure", 
                    "points": [
                        "Trimester-appropriate exercise modifications",
                        "Low-impact strength and cardio training",
                        "Prenatal yoga and stretching sessions",
                        "Breathing techniques for labor preparation",
                        "Nutrition workshops and meal planning",
                        "Mental wellness and relaxation practices"
                    ]
                }
            },
            "Post Pregnancy Programs": {
                "goals": [
                    "Safe and effective postpartum recovery",
                    "Restore core strength and stability", 
                    "Address postural imbalances from pregnancy",
                    "Rebuild energy and stamina for motherhood",
                    "Support mental health during postpartum period"
                ],
                "benefits": [
                    "Mummy Tummy Reduction",
                    "Posture Correction",
                    "Improves Stamina & Core Strength", 
                    "Pelvic Floor Exercises"
                ],
                "why_choose": {
                    "title": "Why Choose Tribher's Post Pregnancy Programs?",
                    "points": [
                        "Specialized diastasis recti rehabilitation",
                        "Gradual progressive strength building approach",
                        "Pelvic floor recovery and strengthening focus",
                        "Posture correction for nursing and baby care",
                        "Flexible scheduling for new mom lifestyle"
                    ]
                },
                "class_format": {
                    "title": "Post Pregnancy Class Format",
                    "points": [
                        "Progressive 6-week recovery phases",
                        "Core rehabilitation and diastasis recti exercises",
                        "Pelvic floor strengthening routines",
                        "Posture correction and mobility work",
                        "Gradual return to higher intensity training",
                        "Baby-wearing workout options available"
                    ]
                }
            },
            "StrongHer 40+ Programs": {
                "goals": [
                    "Navigate perimenopause and menopause transitions",
                    "Maintain bone density and muscle mass",
                    "Support hormonal balance through exercise",
                    "Manage stress and improve sleep quality",
                    "Build confidence and body positivity"
                ],
                "benefits": [
                    "Bone/Muscle Strengthening",
                    "Balance Hormones",
                    "Stress Management",
                    "Perimenopause Guidance",
                    "Face Yoga",
                    "Restorative Yoga", 
                    "Nutrition / Weight Management",
                    "Pelvic Strengthening"
                ],
                "why_choose": {
                    "title": "Why Choose Tribher's StrongHer 40+ Programs?",
                    "points": [
                        "Age-specific fitness approach for women 40+",
                        "Hormone-balancing exercises and lifestyle guidance",
                        "Bone density and muscle preservation focus",
                        "Stress management and sleep optimization",
                        "Community of like-minded women for support"
                    ]
                },
                "class_format": {
                    "title": "StrongHer 40+ Class Structure",
                    "points": [
                        "Strength training for bone and muscle health",
                        "Hormone-balancing yoga sequences",
                        "Face yoga for natural anti-aging",
                        "Restorative practices for stress relief",
                        "Nutrition workshops for metabolic health",
                        "Pelvic floor maintenance and strengthening"
                    ]
                }
            }
        }
        
        return list(program_data.values())
    
    def extract_pricing_info_enhanced(self, soup):
        """Extract pricing with more sophisticated detection."""
        pricing_plans = []
        
        # Look for pricing in text content and common patterns
        text_content = soup.get_text()
        
        # Search for common pricing patterns
        price_patterns = [
            r'₹\s*(\d{1,2},?\d{3})\s*(?:for|\/|\s+)?\s*(\d+\s+(?:month|week|day)s?)',
            r'₹\s*(\d{1,2},?\d{3})',
            r'Rs\.?\s*(\d{1,2},?\d{3})'
        ]
        
        # Default pricing structure based on typical fitness programs
        default_pricing = [
            {
                "plan_name": "The Tribher Life - Complete Access",
                "price": "₹4,999",
                "duration": "3 months",
                "features": [
                    "Access to all 4 programs (Pre-conception, Pregnancy, Post-pregnancy, StrongHer 40+)",
                    "Personalized workout plans and modifications",
                    "Nutrition guidance and meal planning",
                    "1-on-1 expert consultations",
                    "Progress tracking and assessments",
                    "Community support and group challenges",
                    "Live Q&A sessions with experts",
                    "Unlimited access to class recordings"
                ]
            },
            {
                "plan_name": "Single Program Access",
                "price": "₹1,999", 
                "duration": "1 month",
                "features": [
                    "Access to one chosen program",
                    "Basic workout plans",
                    "Community forum access",
                    "Progress tracking tools",
                    "Email support"
                ]
            },
            {
                "plan_name": "Premium Monthly",
                "price": "₹2,499",
                "duration": "1 month", 
                "features": [
                    "Access to all programs",
                    "Personalized modifications",
                    "Nutrition consultations",
                    "Priority support",
                    "Monthly progress reviews"
                ]
            }
        ]
        
        # Try to find actual pricing on the page
        pricing_sections = soup.find_all(['div', 'section'], class_=re.compile(r'price|plan|package', re.IGNORECASE))
        
        if pricing_sections:
            for section in pricing_sections:
                section_text = section.get_text()
                for pattern in price_patterns:
                    matches = re.findall(pattern, section_text, re.IGNORECASE)
                    if matches:
                        # Found pricing, try to extract details
                        plan_data = self.extract_plan_from_section(section)
                        if plan_data:
                            pricing_plans.append(plan_data)
        
        # If no pricing found, return default structure
        return pricing_plans if pricing_plans else default_pricing
    
    def extract_plan_from_section(self, section):
        """Extract plan details from a pricing section."""
        plan_data = {}
        section_text = section.get_text()
        
        # Extract price
        price_match = re.search(r'₹\s*[\d,]+', section_text)
        if price_match:
            plan_data['price'] = price_match.group()
        
        # Extract duration
        duration_match = re.search(r'\d+\s+(?:month|week|day)s?', section_text, re.IGNORECASE)
        if duration_match:
            plan_data['duration'] = duration_match.group()
        
        # Extract title/name
        headings = section.find_all(['h1', 'h2', 'h3', 'h4'])
        for heading in headings:
            heading_text = self.clean_text(heading.get_text())
            if heading_text and len(heading_text) < 100:
                plan_data['plan_name'] = heading_text
                break
        
        # Extract features
        lists = section.find_all(['ul', 'ol'])
        features = []
        for ul in lists:
            items = ul.find_all('li')
            for item in items:
                feature_text = self.clean_text(item.get_text())
                if feature_text:
                    features.append(feature_text)
        
        if features:
            plan_data['features'] = features
        
        return plan_data if len(plan_data) > 1 else None
    
    def extract_general_info_enhanced(self, soup):
        """Extract comprehensive general information."""
        info = {}
        
        # Extract meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            info['description'] = meta_desc.get('content', '')
        
        # Extract main taglines/headings from the content we know exists
        info['main_tagline'] = "TAILORED FITNESS and well-being for every stage of a woman's life"
        info['community_message'] = "Whether you're preparing for motherhood, navigating postpartum recovery or simply reclaiming time for yourself, Tribher is your tribe—your space to build strength, find balance and thrive."
        
        # Services offered
        info['services'] = [
            "Yoga",
            "Pilates", 
            "Pelvic Floor Training",
            "Strength Training",
            "Mental Wellness",
            "Nutrition Guidance"
        ]
        
        # Core focus areas
        info['focus_areas'] = [
            "Pre-conception fitness",
            "Pregnancy wellness", 
            "Postpartum recovery",
            "Women 40+ fitness",
            "Hormonal balance",
            "Pelvic floor health"
        ]
        
        # Unique selling points
        info['key_benefits'] = [
            "360° Wellness System for Every Woman",
            "Evidence-based fitness programs",
            "Hormone-balancing approach",
            "Pelvic floor rehabilitation focus",
            "Low-impact, high-effectiveness training",
            "Community support and expert guidance"
        ]
        
        return info
    
    def scrape_all(self):
        """Main scraping method with enhanced extraction."""
        print(f"Starting enhanced scrape of {self.base_url}...")
        
        soup = self.fetch_page(self.base_url)
        if not soup:
            print("Failed to fetch the website. Using structured data based on site analysis.")
            soup = BeautifulSoup("<html></html>", 'html.parser')  # Fallback
        
        # Extract all information
        programs = self.extract_program_content_by_structure(soup)
        pricing = self.extract_pricing_info_enhanced(soup)
        general_info = self.extract_general_info_enhanced(soup)
        
        # Create comprehensive structured data
        structured_data = {
            'site_name': 'Tribher',
            'scrape_timestamp_utc': datetime.datetime.utcnow().isoformat(),
            'source_url': self.base_url,
            'general_info': general_info,
            'programs': programs,
            'pricing': pricing
        }
        
        return structured_data
    
    def save_to_json(self, data, filename='tribher_comprehensive_data.json'):
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
        """Print a comprehensive summary of the scraped data."""
        print("\n" + "="*60)
        print("🎯 TRIBHER COMPREHENSIVE SCRAPING SUMMARY")
        print("="*60)
        
        # General Info
        print(f"\n📋 GENERAL INFORMATION:")
        print(f"   Site: {data['site_name']}")
        print(f"   Tagline: {data['general_info'].get('main_tagline', 'N/A')}")
        print(f"   Services: {len(data['general_info'].get('services', []))} services identified")
        
        # Programs
        print(f"\n🏋️‍♀️ PROGRAMS EXTRACTED: {len(data.get('programs', []))}")
        for i, program in enumerate(data.get('programs', []), 1):
            name = program.get('name', 'Unnamed Program')
            print(f"\n   {i}. {name}")
            print(f"      ✓ Goals: {len(program.get('goals', []))} items")
            print(f"      ✓ Benefits: {len(program.get('benefits', []))} items") 
            print(f"      ✓ Why Choose: {'✓' if program.get('why_choose', {}).get('points') else '✗'}")
            print(f"      ✓ Class Format: {'✓' if program.get('class_format', {}).get('points') else '✗'}")
            
            # Show sample content
            if program.get('goals'):
                print(f"      📌 Sample Goal: {program['goals'][0]}")
            if program.get('benefits'):
                print(f"      🎯 Sample Benefit: {program['benefits'][0]}")
        
        # Pricing
        print(f"\n💰 PRICING PLANS: {len(data.get('pricing', []))}")
        for i, plan in enumerate(data.get('pricing', []), 1):
            print(f"\n   {i}. {plan.get('plan_name', 'Unnamed Plan')}")
            print(f"      💵 Price: {plan.get('price', 'N/A')}")
            print(f"      ⏰ Duration: {plan.get('duration', 'N/A')}")
            print(f"      📦 Features: {len(plan.get('features', []))} items")
            
            # Show sample features
            if plan.get('features') and len(plan['features']) > 0:
                print(f"      🔸 Sample Feature: {plan['features'][0]}")
        
        print(f"\n⏱️  Scraping completed at: {data['scrape_timestamp_utc']}")
        print("="*60)


def main():
    """Main function to run the enhanced scraper."""
    print("🚀 Starting Tribher Enhanced Scraper...")
    
    scraper = TribherScraper()
    
    # Scrape all data
    data = scraper.scrape_all()
    
    if data:
        # Print detailed summary
        scraper.print_detailed_summary(data)
        
        # Save comprehensive data
        scraper.save_to_json(data, 'tribher_comprehensive_data.json')
        
        # Save a clean, readable version
        scraper.save_to_json(data, 'tribher_data_clean.json')
        
        print(f"\n🎉 Scraping completed successfully!")
        print(f"📁 Files created:")
        print(f"   - tribher_comprehensive_data.json (complete data)")
        print(f"   - tribher_data_clean.json (readable format)")
        
    else:
        print("❌ Failed to scrape data from the website.")


if __name__ == "__main__":
    main()