"""
Advanced User Profile Generator

This module generates realistic user profiles with diverse demographics,
names from multiple cultures, and randomized attributes for Gmail account creation.
"""

import random
import json
import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
import string
import secrets

# Optional unidecode import
try:
    from unidecode import unidecode
    UNIDECODE_AVAILABLE = True
except ImportError:
    UNIDECODE_AVAILABLE = False
    def unidecode(text):
        """Fallback function when unidecode is not available"""
        # Simple ASCII conversion for basic cases
        return text.encode('ascii', 'ignore').decode('ascii')

from .config_manager import ConfigManager, GmailCreatorConfig

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile data class"""
    first_name: str
    last_name: str
    username: str
    password: str
    birth_year: int
    birth_month: int
    birth_day: int
    gender: str
    locale: str
    timezone: str
    country: str
    city: str
    phone_country_code: Optional[str] = None
    recovery_email: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.birth_year - ((today.month, today.day) < (self.birth_month, self.birth_day))
    
    def to_dict(self) -> Dict:
        """Convert profile to dictionary"""
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "password": self.password,
            "birth_date": f"{self.birth_year}-{self.birth_month:02d}-{self.birth_day:02d}",
            "gender": self.gender,
            "locale": self.locale,
            "timezone": self.timezone,
            "country": self.country,
            "city": self.city,
            "age": self.age,
            "phone_country_code": self.phone_country_code,
            "recovery_email": self.recovery_email
        }


class NameDatabase:
    """Database of names from various cultures and countries"""
    
    def __init__(self):
        self.names_data = {
            "english": {
                "first_names": {
                    "male": [
                        "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
                        "Thomas", "Christopher", "Charles", "Daniel", "Matthew", "Anthony", "Mark",
                        "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian",
                        "George", "Timothy", "Ronald", "Jason", "Edward", "Jeffrey", "Ryan", "Jacob",
                        "Gary", "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott",
                        "Brandon", "Benjamin", "Samuel", "Frank", "Gregory", "Raymond", "Alexander",
                        "Patrick", "Jack", "Dennis", "Jerry", "Tyler", "Aaron", "Jose", "Henry"
                    ],
                    "female": [
                        "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan",
                        "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Dorothy", "Sandra",
                        "Ashley", "Kimberly", "Donna", "Emily", "Margaret", "Carol", "Michelle",
                        "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Laura", "Sharon",
                        "Cynthia", "Kathleen", "Amy", "Shirley", "Angela", "Helen", "Anna", "Brenda",
                        "Emma", "Olivia", "Sophia", "Ava", "Isabella", "Mia", "Abigail", "Grace",
                        "Hannah", "Addison", "Mackenzie", "Sydney", "Hailey", "Jasmine", "Julia"
                    ]
                },
                "last_names": [
                    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
                    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
                    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
                    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
                    "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
                    "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner"
                ]
            },
            "spanish": {
                "first_names": {
                    "male": [
                        "Jose", "Luis", "Carlos", "Juan", "Miguel", "Antonio", "Francisco", "Manuel",
                        "Jesus", "David", "Daniel", "Jorge", "Alejandro", "Pedro", "Angel", "Diego",
                        "Rafael", "Fernando", "Ricardo", "Pablo", "Eduardo", "Sergio", "Roberto",
                        "Javier", "Adrián", "Andrés", "Óscar", "Víctor", "Raúl", "Rubén", "Mario",
                        "Álvaro", "Gonzalo", "Hugo", "Iván", "Marcos", "Diego", "Lorenzo", "Joaquín"
                    ],
                    "female": [
                        "Maria", "Carmen", "Josefa", "Isabel", "Ana", "Dolores", "Antonia", "Francisca",
                        "Laura", "Teresa", "Pilar", "Mercedes", "Julia", "Concepción", "Manuela",
                        "Rosa", "Cristina", "Marta", "Angeles", "Lucia", "Josefina", "Montserrat",
                        "Paula", "Elena", "Sara", "Patricia", "Beatriz", "Silvia", "Raquel",
                        "Rocío", "Inmaculada", "Mónica", "Nuria", "Susana", "Yolanda", "Margarita"
                    ]
                },
                "last_names": [
                    "García", "Rodríguez", "González", "Fernández", "López", "Martínez", "Sánchez",
                    "Pérez", "Gómez", "Martín", "Jiménez", "Ruiz", "Hernández", "Díaz", "Moreno",
                    "Muñoz", "Álvarez", "Romero", "Alonso", "Gutiérrez", "Navarro", "Torres",
                    "Domínguez", "Vázquez", "Ramos", "Gil", "Ramírez", "Serrano", "Blanco", "Suárez",
                    "Molina", "Morales", "Ortega", "Delgado", "Castro", "Ortiz", "Rubio", "Marín"
                ]
            },
            "french": {
                "first_names": {
                    "male": [
                        "Jean", "Pierre", "Michel", "André", "Philippe", "Alain", "Bernard", "Claude",
                        "Paul", "Daniel", "Henri", "François", "Jacques", "Louis", "Marcel", "Robert",
                        "Patrick", "Christian", "Roger", "Gérard", "René", "Raymond", "Lucien",
                        "Antoine", "Nicolas", "Olivier", "Pascal", "Vincent", "Julien", "Sébastien",
                        "Thomas", "Alexandre", "Maxime", "Benjamin", "Lucas", "Mathieu", "Florian"
                    ],
                    "female": [
                        "Marie", "Jeanne", "Françoise", "Monique", "Catherine", "Nathalie", "Isabelle",
                        "Sylvie", "Martine", "Nicole", "Céline", "Brigitte", "Annie", "Christine",
                        "Valérie", "Patricia", "Sandrine", "Caroline", "Véronique", "Dominique",
                        "Christiane", "Chantal", "Jacqueline", "Laurence", "Agnès", "Sophie",
                        "Camille", "Emma", "Clara", "Sarah", "Manon", "Léa", "Chloe", "Jade"
                    ]
                },
                "last_names": [
                    "Martin", "Bernard", "Thomas", "Petit", "Robert", "Richard", "Durand", "Dubois",
                    "Moreau", "Laurent", "Simon", "Michel", "Lefebvre", "Leroy", "Roux", "David",
                    "Bertrand", "Morel", "Fournier", "Girard", "Bonnet", "Dupont", "Lambert",
                    "Fontaine", "Rousseau", "Vincent", "Muller", "Lefevre", "Faure", "Andre",
                    "Mercier", "Blanc", "Guerin", "Boyer", "Garnier", "Chevalier", "Francois"
                ]
            },
            "german": {
                "first_names": {
                    "male": [
                        "Michael", "Andreas", "Thomas", "Klaus", "Wolfgang", "Jürgen", "Günter",
                        "Stefan", "Peter", "Uwe", "Frank", "Rainer", "Bernd", "Dieter", "Hans",
                        "Christian", "Werner", "Helmut", "Horst", "Manfred", "Gerhard", "Harald",
                        "Alexander", "Sebastian", "Daniel", "Martin", "Jan", "Florian", "Benjamin",
                        "Tobias", "Matthias", "Markus", "Felix", "Max", "Paul", "Leon", "Noah"
                    ],
                    "female": [
                        "Ursula", "Helga", "Ingrid", "Petra", "Monika", "Gabriele", "Andrea",
                        "Sabine", "Susanne", "Claudia", "Barbara", "Brigitte", "Birgit", "Karin",
                        "Martina", "Christine", "Angelika", "Nicole", "Stefanie", "Silke", "Katrin",
                        "Sandra", "Julia", "Anna", "Maria", "Lisa", "Sarah", "Laura", "Michelle",
                        "Hannah", "Lea", "Emily", "Marie", "Sophie", "Lena", "Emma", "Mia"
                    ]
                },
                "last_names": [
                    "Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner",
                    "Becker", "Schulz", "Hoffmann", "Schäfer", "Koch", "Bauer", "Richter",
                    "Klein", "Wolf", "Schröder", "Neumann", "Schwarz", "Zimmermann", "Braun",
                    "Krüger", "Hofmann", "Hartmann", "Lange", "Schmitt", "Werner", "Schmitz",
                    "Krause", "Meier", "Lehmann", "Schmid", "Schulze", "Maier", "Köhler"
                ]
            },
            "arabic": {
                "first_names": {
                    "male": [
                        "Ahmed", "Mohammed", "Omar", "Ali", "Hassan", "Hussein", "Youssef", "Amr",
                        "Khaled", "Mahmoud", "Tamer", "Hany", "Sherif", "Mostafa", "Karim", "Rami",
                        "Sami", "Nader", "Waleed", "Magdy", "Ashraf", "Emad", "Essam", "Gamal",
                        "Hossam", "Ibrahim", "Ismail", "Medhat", "Osama", "Reda", "Tarek", "Wael",
                        "Adel", "Akram", "Ayman", "Basel", "Fadi", "Hani", "Imad", "Jamal"
                    ],
                    "female": [
                        "Fatima", "Aisha", "Mariam", "Zeinab", "Khadija", "Amina", "Nour", "Sara",
                        "Rana", "Dina", "Hala", "Layla", "Maya", "Nada", "Reem", "Sama", "Tala",
                        "Yasmin", "Dalia", "Farah", "Heba", "Jana", "Lina", "Mona", "Nora", "Rania",
                        "Salma", "Yara", "Asma", "Basma", "Ghada", "Hanan", "Iman", "Jihan",
                        "Karima", "Lubna", "Nagwa", "Rawda", "Sawsan", "Wafaa", "Zeinab"
                    ]
                },
                "last_names": [
                    "Ahmed", "Ali", "Hassan", "Mohamed", "Ibrahim", "Mahmoud", "Omar", "Youssef",
                    "Abdel", "Saeed", "Farouk", "Rashid", "Nasser", "Saleh", "Khalil", "Mansour",
                    "Ismail", "Zaki", "Fouad", "Abdallah", "Salem", "Amin", "Gamal", "Kamel",
                    "Mostafa", "Tawfik", "Hegazy", "Shawky", "Rady", "Soliman", "Zaher", "Darwish",
                    "Othman", "Qasem", "Ramadan", "Shahin", "Tantawy", "Wahba", "Yassin"
                ]
            },
            "italian": {
                "first_names": {
                    "male": [
                        "Giuseppe", "Antonio", "Marco", "Andrea", "Francesco", "Mario", "Luigi",
                        "Angelo", "Vincenzo", "Pietro", "Salvatore", "Carlo", "Franco", "Domenico",
                        "Bruno", "Paolo", "Michele", "Sergio", "Massimo", "Roberto", "Stefano",
                        "Alessandro", "Giovanni", "Claudio", "Maurizio", "Fabio", "Daniele",
                        "Simone", "Federico", "Matteo", "Luca", "Nicola", "Riccardo", "Davide"
                    ],
                    "female": [
                        "Maria", "Anna", "Giulia", "Rosa", "Angela", "Giovanna", "Teresa", "Luisa",
                        "Francesca", "Antonia", "Giuseppina", "Elena", "Caterina", "Lucia", "Carla",
                        "Bruna", "Gina", "Patrizia", "Silvana", "Rita", "Paola", "Laura", "Franca",
                        "Lorenza", "Daniela", "Claudia", "Antonella", "Stefania", "Alessandra",
                        "Barbara", "Roberta", "Emanuela", "Cristina", "Chiara", "Federica"
                    ]
                },
                "last_names": [
                    "Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo",
                    "Ricci", "Marino", "Greco", "Bruno", "Gallo", "Conti", "De Luca", "Costa",
                    "Giordano", "Mancini", "Rizzo", "Lombardi", "Moretti", "Barbieri", "Fontana",
                    "Santoro", "Mariani", "Rinaldi", "Caruso", "Ferrara", "Galli", "Martini",
                    "Leone", "Longo", "Gentile", "Martinelli", "Vitale", "Lombardo", "Serra"
                ]
            }
        }
    
    def get_random_name(self, culture: str = None, gender: str = None) -> Tuple[str, str, str]:
        """Get random first name, last name, and culture"""
        if culture is None:
            culture = random.choice(list(self.names_data.keys()))
        
        if gender is None:
            gender = random.choice(["male", "female"])
        
        culture_data = self.names_data.get(culture, self.names_data["english"])
        
        first_name = random.choice(culture_data["first_names"][gender])
        last_name = random.choice(culture_data["last_names"])
        
        return first_name, last_name, culture


class UserProfileGenerator:
    """Generate realistic user profiles for Gmail account creation"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.config
        self.name_db = NameDatabase()
        
        # Country/locale data
        self.locale_data = {
            "en_US": {"country": "United States", "timezone": "America/New_York", "phone_code": "+1"},
            "en_GB": {"country": "United Kingdom", "timezone": "Europe/London", "phone_code": "+44"},
            "en_CA": {"country": "Canada", "timezone": "America/Toronto", "phone_code": "+1"},
            "en_AU": {"country": "Australia", "timezone": "Australia/Sydney", "phone_code": "+61"},
            "es_ES": {"country": "Spain", "timezone": "Europe/Madrid", "phone_code": "+34"},
            "es_MX": {"country": "Mexico", "timezone": "America/Mexico_City", "phone_code": "+52"},
            "fr_FR": {"country": "France", "timezone": "Europe/Paris", "phone_code": "+33"},
            "de_DE": {"country": "Germany", "timezone": "Europe/Berlin", "phone_code": "+49"},
            "it_IT": {"country": "Italy", "timezone": "Europe/Rome", "phone_code": "+39"},
            "ar_EG": {"country": "Egypt", "timezone": "Africa/Cairo", "phone_code": "+20"},
            "ar_SA": {"country": "Saudi Arabia", "timezone": "Asia/Riyadh", "phone_code": "+966"}
        }
        
        # Cities by country
        self.cities = {
            "United States": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia"],
            "United Kingdom": ["London", "Birmingham", "Manchester", "Liverpool", "Leeds", "Sheffield"],
            "Canada": ["Toronto", "Montreal", "Vancouver", "Calgary", "Ottawa", "Edmonton"],
            "Australia": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast"],
            "Spain": ["Madrid", "Barcelona", "Valencia", "Seville", "Zaragoza", "Málaga"],
            "Mexico": ["Mexico City", "Guadalajara", "Monterrey", "Puebla", "Toluca", "Tijuana"],
            "France": ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes"],
            "Germany": ["Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt", "Stuttgart"],
            "Italy": ["Rome", "Milan", "Naples", "Turin", "Palermo", "Genoa"],
            "Egypt": ["Cairo", "Alexandria", "Giza", "Shubra El Kheima", "Port Said", "Suez"],
            "Saudi Arabia": ["Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Khobar"]
        }
    
    def generate_username(self, first_name: str, last_name: str) -> str:
        """Generate username variations"""
        first_clean = unidecode(first_name.lower())
        last_clean = unidecode(last_name.lower())
        
        # Remove special characters
        first_clean = re.sub(r'[^a-z]', '', first_clean)
        last_clean = re.sub(r'[^a-z]', '', last_clean)
        
        patterns = [
            f"{first_clean}.{last_clean}",
            f"{first_clean}{last_clean}",
            f"{first_clean}_{last_clean}",
            f"{first_clean[0]}{last_clean}",
            f"{first_clean}{last_clean[0]}",
            f"{first_clean}.{last_clean}{random.randint(1, 99)}",
            f"{first_clean}{random.randint(10, 99)}",
            f"{first_clean}{last_clean}{random.randint(1990, 2005)}"
        ]
        
        return random.choice(patterns)
    
    def generate_password(self) -> str:
        """Generate secure password"""
        if self.config.user_profile.use_complex_passwords:
            # Complex password with mixed case, numbers, and symbols
            chars = string.ascii_letters + string.digits + "!@#$%^&*"
            password = ''.join(secrets.choice(chars) for _ in range(self.config.user_profile.password_length))
            
            # Ensure password has at least one of each type
            if not any(c.islower() for c in password):
                password = password[:-1] + random.choice(string.ascii_lowercase)
            if not any(c.isupper() for c in password):
                password = password[:-1] + random.choice(string.ascii_uppercase)
            if not any(c.isdigit() for c in password):
                password = password[:-1] + random.choice(string.digits)
            if not any(c in "!@#$%^&*" for c in password):
                password = password[:-1] + random.choice("!@#$%^&*")
                
            return password
        else:
            # Simple but secure password
            words = ["Shadow", "Secure", "Access", "Digital", "Quick", "Smart", "Power", "Elite"]
            word = random.choice(words)
            numbers = random.randint(100, 999)
            symbols = random.choice(["!", "@", "#", "$"])
            return f"{word}{numbers}{symbols}"
    
    def generate_birth_date(self) -> Tuple[int, int, int]:
        """Generate realistic birth date"""
        min_year, max_year = self.config.user_profile.birth_year_range
        year = random.randint(min_year, max_year)
        month = random.randint(1, 12)
        
        # Days in month
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
            days_in_month[1] = 29  # Leap year
        
        day = random.randint(1, days_in_month[month - 1])
        
        return year, month, day
    
    def select_locale_and_culture(self) -> Tuple[str, str]:
        """Select locale and matching culture"""
        locale = random.choice(self.config.user_profile.supported_locales)
        
        # Map locale to culture for name generation
        culture_mapping = {
            "en_US": "english",
            "en_GB": "english", 
            "en_CA": "english",
            "en_AU": "english",
            "es_ES": "spanish",
            "es_MX": "spanish",
            "fr_FR": "french",
            "de_DE": "german",
            "it_IT": "italian",
            "ar_EG": "arabic",
            "ar_SA": "arabic"
        }
        
        culture = culture_mapping.get(locale, "english")
        return locale, culture
    
    def generate_profile(self) -> UserProfile:
        """Generate a complete user profile"""
        logger.debug("Generating user profile")
        
        # Select locale and culture
        locale, culture = self.select_locale_and_culture()
        locale_info = self.locale_data[locale]
        
        # Generate names
        gender = random.choice(["male", "female"])
        first_name, last_name, _ = self.name_db.get_random_name(culture, gender)
        
        # Generate other attributes
        username = self.generate_username(first_name, last_name)
        password = self.generate_password()
        birth_year, birth_month, birth_day = self.generate_birth_date()
        
        # Location
        country = locale_info["country"]
        city = random.choice(self.cities.get(country, ["Unknown City"]))
        
        # Create profile
        profile = UserProfile(
            first_name=first_name,
            last_name=last_name,
            username=username,
            password=password,
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day,
            gender=gender,
            locale=locale,
            timezone=locale_info["timezone"],
            country=country,
            city=city,
            phone_country_code=locale_info["phone_code"]
        )
        
        logger.debug(f"Generated profile: {profile.full_name} ({profile.username})")
        return profile
    
    def generate_multiple_profiles(self, count: int) -> List[UserProfile]:
        """Generate multiple user profiles"""
        profiles = []
        for i in range(count):
            profile = self.generate_profile()
            profiles.append(profile)
            
            # Ensure uniqueness of usernames
            existing_usernames = {p.username for p in profiles[:-1]}
            attempts = 0
            while profile.username in existing_usernames and attempts < 10:
                profile.username = self.generate_username(profile.first_name, profile.last_name)
                attempts += 1
        
        return profiles
    
    def save_profiles_to_file(self, profiles: List[UserProfile], file_path: str):
        """Save profiles to JSON file"""
        profiles_data = [profile.to_dict() for profile in profiles]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(profiles_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(profiles)} profiles to {file_path}")
    
    def load_profiles_from_file(self, file_path: str) -> List[UserProfile]:
        """Load profiles from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            profiles_data = json.load(f)
        
        profiles = []
        for data in profiles_data:
            # Parse birth date
            birth_parts = data['birth_date'].split('-')
            birth_year = int(birth_parts[0])
            birth_month = int(birth_parts[1])
            birth_day = int(birth_parts[2])
            
            profile = UserProfile(
                first_name=data['first_name'],
                last_name=data['last_name'],
                username=data['username'],
                password=data['password'],
                birth_year=birth_year,
                birth_month=birth_month,
                birth_day=birth_day,
                gender=data['gender'],
                locale=data['locale'],
                timezone=data['timezone'],
                country=data['country'],
                city=data['city'],
                phone_country_code=data.get('phone_country_code'),
                recovery_email=data.get('recovery_email')
            )
            profiles.append(profile)
        
        logger.info(f"Loaded {len(profiles)} profiles from {file_path}")
        return profiles


# Example usage and testing
if __name__ == "__main__":
    from .config_manager import ConfigManager
    
    # Create config manager
    config_manager = ConfigManager()
    config_manager.setup_logging()
    
    # Create profile generator
    generator = UserProfileGenerator(config_manager)
    
    # Generate some profiles
    profiles = generator.generate_multiple_profiles(5)
    
    # Display profiles
    for profile in profiles:
        print(f"Name: {profile.full_name}")
        print(f"Username: {profile.username}")
        print(f"Email: {profile.username}@gmail.com")
        print(f"Password: {profile.password}")
        print(f"Age: {profile.age}")
        print(f"Location: {profile.city}, {profile.country}")
        print(f"Locale: {profile.locale}")
        print("-" * 50)
    
    # Save to file
    generator.save_profiles_to_file(profiles, "test_profiles.json")