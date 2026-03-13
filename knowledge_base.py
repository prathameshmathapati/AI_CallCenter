import json
import os
import threading
from functools import lru_cache

class MultilingualKnowledgeBase:
    def __init__(self):
        """Initialize multilingual knowledge base"""
        self.faqs = []
        self.products = []
        self.orders = []
        
        # Supported languages
        self.supported_languages = ['en', 'hi', 'es', 'fr', 'de', 'pt']
        
        # Language names
        self.language_names = {
            'en': 'English',
            'hi': 'Hindi',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'pt': 'Portuguese'
        }

        # RLock allows the same thread to re-acquire (safer than Lock)
        self._lock = threading.RLock()
        
        # Load data
        self.load_knowledge_base()
    
    # ============================================================
    # LANGUAGE DETECTION  - result cached per unique text input
    # ============================================================
    @lru_cache(maxsize=512)
    def detect_language(self, text):
        """Detect language of text"""
        try:
            from langdetect import detect, LangDetectException
            
            lang = detect(text)
            
            # Map variants to base language
            lang_mapping = {
                'en': 'en',
                'hi': 'hi',
                'es': 'es',
                'fr': 'fr',
                'de': 'de',
                'pt': 'pt',
                'mr': 'hi',  # Marathi → Hindi
                'bn': 'hi',  # Bengali → Hindi
                'ta': 'hi',  # Tamil → Hindi
            }
            
            detected = lang_mapping.get(lang, 'en')
            
            # Fallback to English if not supported
            if detected not in self.supported_languages:
                detected = 'en'
            
            print(f"🌍 Detected language: {self.language_names.get(detected, detected)}")
            return detected
            
        except Exception as e:
            print(f"⚠️ Could not detect language: {e}, defaulting to English")
            return 'en'
    
    # ============================================================
    # LOAD  - reads files once at startup, DRY helper
    # ============================================================
    def load_knowledge_base(self):
        """Load multilingual knowledge base"""

        def _load(filename, label, warn_missing=True):
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"✅ Loaded {len(data)} {label}")
                    return data
                except Exception as e:
                    print(f"⚠️ Could not load {filename}: {e}")
                    return []
            else:
                if warn_missing:
                    print(f"❌ WARNING: {filename} NOT FOUND")
                    print(f"   Current directory: {os.getcwd()}")
                    print(f"   Files in directory: {os.listdir('.')}")
                else:
                    print(f"⚠️ {filename} not found - order lookup will not work")
                return []

        self.faqs     = _load('faqs_multilingual.json',     'multilingual FAQs')
        self.products = _load('products_multilingual.json', 'multilingual products')
        self.orders   = _load('orders.json',                'orders', warn_missing=False)

    # ============================================================
    # FAQ SEARCH  - cached per (query, language) pair
    # ============================================================
    @lru_cache(maxsize=256)
    def search_faqs(self, query, language='en'):
        """Search FAQs in specific language"""
        query_lower = query.lower()
        results = []

        with self._lock:
            faqs_snapshot = list(self.faqs)
        
        for faq in faqs_snapshot:
            # Get text in requested language, fallback to English
            faq_data = faq.get(language, faq.get('en', {}))
            
            if not faq_data:
                continue
            
            question_lower = faq_data.get('question', '').lower()
            answer_lower = faq_data.get('answer', '').lower()
            
            # Create searchable text
            searchable_text = question_lower + ' ' + answer_lower
            
            # Count keyword matches
            query_words = query_lower.split()
            matches = 0
            
            for word in query_words:
                if len(word) > 3:  # Skip short words
                    if word in searchable_text:
                        matches += 1
            
            if matches > 0:
                results.append({
                    'faq': faq_data,
                    'relevance': matches
                })
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return [r['faq'] for r in results[:3]]
    
    # ============================================================
    # PRODUCT SEARCH  - cached per (query, language) pair
    # ============================================================
    @lru_cache(maxsize=256)
    def search_products(self, query, language='en'):
        """Search products in specific language"""
        query_lower = query.lower()
        results = []

        with self._lock:
            products_snapshot = list(self.products)
        
        for product in products_snapshot:
            # Get product in requested language
            prod_data = product.get(language, product.get('en', {}))
            
            if not prod_data:
                continue
            
            # Create searchable text from all product fields
            searchable_text = (
                f"{prod_data.get('name', '')} "
                f"{prod_data.get('price', '')} "
                f"{prod_data.get('features', '')} "
                f"{prod_data.get('description', '')}"
            ).lower()
            
            query_words = query_lower.split()
            matches = 0
            
            for word in query_words:
                if len(word) > 3:
                    if word in searchable_text:
                        matches += 1
            
            if matches > 0:
                results.append({
                    'product': prod_data,
                    'relevance': matches
                })
        
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return [r['product'] for r in results[:3]]
    
    # ============================================================
    # ORDER SEARCH  - no cache (orders change in real-time)
    # ============================================================
    def search_order(self, order_id=None, phone=None):
        """Search for order (language agnostic)"""
        with self._lock:
            orders_snapshot = list(self.orders)

        for order in orders_snapshot:
            if order_id and order['order_id'].upper() == order_id.upper():
                return order
            if phone and order['customer_phone'] == phone:
                return order
        return None
    
    # ============================================================
    # CONTEXT BUILDER  - cached per (query, language) pair
    # ============================================================
    @lru_cache(maxsize=256)
    def get_relevant_context(self, query, language='en'):
        """Get relevant context in specified language"""
        context_parts = []
        
        # Always search FAQs first
        faq_results = self.search_faqs(query, language)
        if faq_results:
            context_parts.append("**Relevant Information from FAQ:**")
            for faq in faq_results:
                context_parts.append(f"Q: {faq['question']}\nA: {faq['answer']}")
        
        # Enhanced product keyword detection
        product_keywords = [
            # English
            'price', 'plan', 'plans', 'cost', 'costs', 'feature', 'features', 
            'product', 'products', 'buy', 'purchase', 'subscription', 'subscriptions',
            'pricing', 'package', 'packages', 'offer', 'offers', 'service', 'services',
            'upgrade', 'tier', 'tiers', 'option', 'options', 'available',
            # Hindi
            'कीमत', 'योजना', 'योजनाएं', 'लागत', 'मूल्य',
            # Spanish
            'precio', 'plan', 'planes', 'costo', 'característica', 'servicio'
        ]
        
        # Check if query is about products/pricing
        query_lower = query.lower()
        is_product_query = any(keyword in query_lower for keyword in product_keywords)
        
        # Also check for question words that might indicate product query
        question_indicators = ['what', 'which', 'tell me', 'show me', 'do you have', 'are there']
        if any(indicator in query_lower for indicator in question_indicators):
            is_product_query = True
        
        # Search products if relevant
        if is_product_query:
            product_results = self.search_products(query, language)
            if product_results:
                context_parts.append("\n**Our Available Plans:**")
                for prod in product_results:
                    context_parts.append(
                        f"• {prod['name']} ({prod['price']}): {prod['features']}"
                    )
        
        # Return context or indicate nothing found
        if context_parts:
            return "\n".join(context_parts)
        else:
            return "No specific information found in knowledge base. Use general customer service knowledge to help."

    # ============================================================
    # CACHE MANAGEMENT
    # ============================================================
    def clear_caches(self):
        """Clear all LRU caches — call after data updates."""
        self.detect_language.cache_clear()
        self.search_faqs.cache_clear()
        self.search_products.cache_clear()
        self.get_relevant_context.cache_clear()
        print("✅ All KB caches cleared.")

    def reload(self):
        """Hot-reload knowledge base files without restarting the server."""
        with self._lock:
            self.load_knowledge_base()
        self.clear_caches()
        print("✅ Knowledge base reloaded.")


# Test the multilingual knowledge base
if __name__ == "__main__":
    print("=" * 60)
    print("TESTING MULTILINGUAL KNOWLEDGE BASE")
    print("=" * 60)
    print()
    
    kb = MultilingualKnowledgeBase()
    
    print("\n" + "=" * 60)
    print("TEST 1: Language Detection")
    print("=" * 60)
    print(f"English text: {kb.detect_language('Hello, how are you?')}")
    print(f"Hindi text: {kb.detect_language('नमस्ते, आप कैसे हैं?')}")
    print(f"Spanish text: {kb.detect_language('Hola, ¿cómo estás?')}")
    
    print("\n" + "=" * 60)
    print("TEST 2: FAQ Search (English)")
    print("=" * 60)
    faq_results = kb.search_faqs("What are your business hours?", 'en')
    for faq in faq_results:
        print(f"Q: {faq['question']}")
        print(f"A: {faq['answer']}\n")
    
    print("=" * 60)
    print("TEST 3: Product Search (English)")
    print("=" * 60)
    product_results = kb.search_products("What plans do you offer?", 'en')
    for prod in product_results:
        print(f"• {prod['name']} ({prod['price']})")
        print(f"  Features: {prod['features']}\n")
    
    print("=" * 60)
    print("TEST 4: Context Retrieval (Plans Query)")
    print("=" * 60)
    context = kb.get_relevant_context("What plans do you offer?", 'en')
    print(context)
    
    print("\n" + "=" * 60)
    print("TEST 5: Context Retrieval (Hours Query)")
    print("=" * 60)
    context = kb.get_relevant_context("What are your hours?", 'en')
    print(context)
    
    print("\n" + "=" * 60)
    print("TEST 6: Hindi Search")
    print("=" * 60)
    context = kb.get_relevant_context("आपके व्यावसायिक घंटे क्या हैं?", 'hi')
    print(context)

    print("\n" + "=" * 60)
    print("TEST 7: Cache Hit (repeat query - should be instant)")
    print("=" * 60)
    context = kb.get_relevant_context("What plans do you offer?", 'en')
    print(context)

    print("\n" + "=" * 60)
    print("TEST 8: Hot Reload")
    print("=" * 60)
    kb.reload()
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)