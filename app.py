from flask import Flask, request, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from flask_cors import CORS
from groq import Groq
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from knowledge_base import MultilingualKnowledgeBase

load_dotenv()

app = Flask(__name__)
CORS(app)

# ============================================================
# GROQ SETUP
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

# ============================================================
# MULTILINGUAL KNOWLEDGE BASE
# ============================================================
print("🔄 Loading multilingual knowledge base...")
kb = MultilingualKnowledgeBase()
print("✅ Multilingual knowledge base ready!")

# ============================================================
# CONVERSATION STORAGE
# ============================================================
conversations = {}

# ============================================================
# VOICE MAPPINGS BY LANGUAGE
# ============================================================
VOICE_MAPPING = {
    'en': 'Polly.Joanna',      # English - Female US
    'hi': 'Polly.Aditi',       # Hindi - Female
    'es': 'Polly.Lucia',       # Spanish - Female Spain
    'fr': 'Polly.Celine',      # French - Female
    'de': 'Polly.Marlene',     # German - Female
    'pt': 'Polly.Vitoria',     # Portuguese - Female Brazil
}

# ============================================================
# LANGUAGE-SPECIFIC GREETINGS
# ============================================================
GREETINGS = {
    'en': "Hi! Thanks for calling. My name is Sarah, and I'm here to help you today.",
    'hi': "नमस्ते! कॉल करने के लिए धन्यवाद। मेरा नाम सारा है, और मैं आज आपकी मदद के लिए यहां हूं।",
    'es': "¡Hola! Gracias por llamar. Mi nombre es Sarah y estoy aquí para ayudarte hoy.",
    'fr': "Bonjour! Merci d'avoir appelé. Je m'appelle Sarah et je suis là pour vous aider aujourd'hui.",
    'de': "Hallo! Danke für Ihren Anruf. Mein Name ist Sarah und ich bin hier, um Ihnen heute zu helfen.",
    'pt': "Olá! Obrigada por ligar. Meu nome é Sarah e estou aqui para ajudá-lo hoje.",
}

HELP_PROMPTS = {
    'en': "How can I help you today?",
    'hi': "आज मैं आपकी कैसे मदद कर सकती हूं?",
    'es': "¿Cómo puedo ayudarte hoy?",
    'fr': "Comment puis-je vous aider aujourd'hui?",
    'de': "Wie kann ich Ihnen heute helfen?",
    'pt': "Como posso ajudá-lo hoje?",
}

ANYTHING_ELSE = {
    'en': "Is there anything else I can help you with?",
    'hi': "क्या कुछ और है जिसमें मैं आपकी मदद कर सकती हूं?",
    'es': "¿Hay algo más en lo que pueda ayudarte?",
    'fr': "Y a-t-il autre chose que je puisse faire pour vous?",
    'de': "Gibt es noch etwas, bei dem ich Ihnen helfen kann?",
    'pt': "Há mais alguma coisa em que eu possa ajudá-lo?",
}

# ============================================================
# MULTILINGUAL SYSTEM PROMPTS
# ============================================================
SYSTEM_PROMPTS = {
    'en': """You are Sarah, a warm and professional customer service representative speaking in English.

Be natural, empathetic, and keep responses SHORT (1-2 sentences max for phone calls).

CRITICAL: Only use information from the CONTEXT below. Never make up details.

CONTEXT:
{context}

Respond naturally in English.""",

    'hi': """आप सारा हैं, एक गर्मजोशी और पेशेवर ग्राहक सेवा प्रतिनिधि जो हिंदी में बात कर रही हैं।

स्वाभाविक, सहानुभूतिपूर्ण रहें, और जवाब छोटे रखें (फोन कॉल के लिए अधिकतम 1-2 वाक्य)।

महत्वपूर्ण: केवल नीचे दिए गए संदर्भ की जानकारी का उपयोग करें। कभी भी विवरण न बनाएं।

संदर्भ:
{context}

हिंदी में स्वाभाविक रूप से जवाब दें।""",

    'es': """Eres Sarah, una representante de servicio al cliente cálida y profesional que habla en español.

Sé natural, empática y mantén las respuestas CORTAS (máximo 1-2 oraciones para llamadas telefónicas).

CRÍTICO: Solo usa información del CONTEXTO a continuación. Nunca inventes detalles.

CONTEXTO:
{context}

Responde naturalmente en español."""
}

# Add more languages as needed
SYSTEM_PROMPTS['fr'] = SYSTEM_PROMPTS['en'].replace('English', 'French').replace('in English', 'in French')
SYSTEM_PROMPTS['de'] = SYSTEM_PROMPTS['en'].replace('English', 'German').replace('in English', 'in German')
SYSTEM_PROMPTS['pt'] = SYSTEM_PROMPTS['en'].replace('English', 'Portuguese').replace('in English', 'in Portuguese')


# ============================================================
# FUNCTION: Get LLM response in specific language
# ============================================================
def get_llm_response(user_message, conversation_history, language='en', caller_phone=None):
    print(f"\n🤖 Processing in {kb.language_names.get(language, language)}...")
    
    # Get context in the detected language
    context = kb.get_relevant_context(user_message, language)
    
    # Check for order queries
    if any(word in user_message.lower() for word in ['order', 'ऑर्डर', 'pedido', 'commande', 'bestellung', 'ordem']):
        order = kb.search_order(phone=caller_phone)
        if order:
            # Add order info to context (in English, LLM will translate)
            context += f"\n\n**Customer's Order:**\nOrder ID: {order['order_id']}\nStatus: {order['status']}\nTracking: {order['tracking']}\nEstimated Delivery: {order['estimated_delivery']}"
    
    print(f"📚 Context: {context[:150]}...")
    
    try:
        # Build messages
        system_prompt = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS['en']).format(context=context)
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history
        for msg in conversation_history:
            if msg['role'] == 'customer':
                messages.append({"role": "user", "content": msg['text']})
            elif msg['role'] == 'ai':
                messages.append({"role": "assistant", "content": msg['text']})
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        # Call Groq
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=120,
            temperature=0.8
        )
        
        ai_text = response.choices[0].message.content.strip()
        ai_text = ai_text.replace('**', '').replace('*', '')
        
        print(f"🤖 Response: {ai_text}")
        return ai_text
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
        # Language-specific error messages
        error_messages = {
            'en': "I'm sorry, I'm having technical difficulty. Let me transfer you to someone who can help.",
            'hi': "मुझे खेद है, मुझे तकनीकी समस्या हो रही है। मैं आपको किसी ऐसे व्यक्ति से जोड़ती हूं जो मदद कर सके।",
            'es': "Lo siento, tengo dificultades técnicas. Déjame transferirte a alguien que pueda ayudar.",
        }
        return error_messages.get(language, error_messages['en'])


# ============================================================
# ROUTE: Answer incoming calls with language detection
# ============================================================
@app.route("/answer", methods=['GET', 'POST'])
def answer_call():
    caller_number = request.values.get('From', 'Browser Test')
    call_sid = request.values.get('CallSid', 'TEST-CALL')
    
    print(f"\n📞 INCOMING CALL")
    print(f"From: {caller_number}")
    print(f"Call ID: {call_sid}")
    
    # Initialize conversation with default English
    conversations[call_sid] = {
        'caller': caller_number,
        'messages': [],
        'language': 'en',  # Will be detected from first message
        'start_time': datetime.now().isoformat()
    }
    
    response = VoiceResponse()
    
    # Greet in English initially (will switch after language detection)
    response.say(
        GREETINGS['en'],
        voice=VOICE_MAPPING['en'],
        language='en-US'
    )
    
    response.pause(length=0.7)
    
    # Listen for first input to detect language
    gather = Gather(
        input='speech',
        action='/process-speech',
        timeout=5,
        speech_timeout='auto',
        language='en-US, hi-IN, es-ES, fr-FR, de-DE, pt-BR',  # Multi-language recognition
        hints='order, ऑर्डर, pedido, hours, घंटे, horas, plan, योजना'
    )
    gather.say(HELP_PROMPTS['en'], voice=VOICE_MAPPING['en'])
    response.append(gather)
    
    response.redirect('/answer')
    
    return str(response)


# ============================================================
# ROUTE: Process speech with language detection
# ============================================================
@app.route("/process-speech", methods=['POST'])
def process_speech():
    # Get data
    if request.is_json:
        data = request.get_json()
        user_speech = data.get('SpeechResult', '')
        call_sid = data.get('CallSid', 'TEST-CALL')
        caller_phone = data.get('From', None)
    else:
        user_speech = request.values.get('SpeechResult', '')
        call_sid = request.values.get('CallSid', 'Unknown')
        caller_phone = request.values.get('From', None)
    
    print(f"\n💬 CUSTOMER SAID: {user_speech}")
    
    # Initialize if needed
    if call_sid not in conversations:
        conversations[call_sid] = {
            'caller': caller_phone or 'Unknown',
            'messages': [],
            'language': 'en',
            'start_time': datetime.now().isoformat()
        }
    
    # Handle empty input
    if not user_speech or len(user_speech.strip()) < 2:
        response = VoiceResponse()
        lang = conversations[call_sid].get('language', 'en')
        voice = VOICE_MAPPING.get(lang, 'Polly.Joanna')
        
        gather = Gather(
            input='speech',
            action='/process-speech',
            timeout=5,
            speech_timeout='auto',
            language=f'{lang}-IN' if lang == 'hi' else f'{lang}-US'
        )
        
        retry_messages = {
            'en': "I didn't catch that. Could you say that again?",
            'hi': "मुझे वह समझ नहीं आया। क्या आप फिर से कह सकते हैं?",
            'es': "No entendí eso. ¿Puedes repetirlo?"
        }
        gather.say(retry_messages.get(lang, retry_messages['en']), voice=voice)
        response.append(gather)
        response.redirect('/answer')
        return str(response)
    
    # DETECT LANGUAGE from first message
    if len(conversations[call_sid]['messages']) == 0:
        detected_lang = kb.detect_language(user_speech)
        conversations[call_sid]['language'] = detected_lang
        print(f"🌍 Language set to: {kb.language_names[detected_lang]}")
    
    # Get detected language
    lang = conversations[call_sid]['language']
    voice = VOICE_MAPPING.get(lang, 'Polly.Joanna')
    
    # Save message
    conversations[call_sid]['messages'].append({
        'role': 'customer',
        'text': user_speech,
        'timestamp': datetime.now().isoformat()
    })
    
    # Check for goodbye in multiple languages
    goodbye_words = ['bye', 'goodbye', 'धन्यवाद बाय', 'अलविदा', 'adiós', 'chau', 
                     'au revoir', 'auf wiedersehen', 'tchau']
    if any(word in user_speech.lower() for word in goodbye_words):
        response = VoiceResponse()
        
        goodbye_messages = {
            'en': "You're very welcome! Thanks for calling. Have a wonderful day!",
            'hi': "आपका स्वागत है! कॉल करने के लिए धन्यवाद। आपका दिन शुभ हो!",
            'es': "¡De nada! Gracias por llamar. ¡Que tengas un día maravilloso!",
        }
        
        response.say(
            goodbye_messages.get(lang, goodbye_messages['en']),
            voice=voice
        )
        response.hangup()
        save_conversation(call_sid)
        return str(response)
    
    # Get AI response in detected language
    ai_response = get_llm_response(
        user_speech,
        conversations[call_sid]['messages'],
        lang,
        caller_phone
    )
    
    # Save AI response
    conversations[call_sid]['messages'].append({
        'role': 'ai',
        'text': ai_response,
        'timestamp': datetime.now().isoformat()
    })
    
    # Build response in detected language
    response = VoiceResponse()
    response.say(ai_response, voice=voice)
    response.pause(length=0.8)
    
    # Continue conversation
    gather = Gather(
        input='speech',
        action='/process-speech',
        timeout=5,
        speech_timeout='auto',
        language=f'{lang}-IN' if lang == 'hi' else f'{lang}-US'
    )
    gather.say(ANYTHING_ELSE.get(lang, ANYTHING_ELSE['en']), voice=voice)
    response.append(gather)
    
    response.redirect('/process-speech-timeout')
    
    return str(response)


# ============================================================
# ROUTE: Timeout handler
# ============================================================
@app.route("/process-speech-timeout", methods=['POST', 'GET'])
def process_speech_timeout():
    call_sid = request.values.get('CallSid', 'Unknown')
    lang = conversations.get(call_sid, {}).get('language', 'en')
    voice = VOICE_MAPPING.get(lang, 'Polly.Joanna')
    
    response = VoiceResponse()
    
    gather = Gather(
        input='speech',
        action='/process-speech',
        timeout=5,
        speech_timeout='auto',
        language=f'{lang}-IN' if lang == 'hi' else f'{lang}-US'
    )
    
    still_there = {
        'en': "Are you still there?",
        'hi': "क्या आप अभी भी हैं?",
        'es': "¿Sigues ahí?",
    }
    gather.say(still_there.get(lang, still_there['en']), voice=voice)
    response.append(gather)
    
    final_goodbye = {
        'en': "Thank you for calling. Have a great day!",
        'hi': "कॉल करने के लिए धन्यवाद। आपका दिन शुभ हो!",
        'es': "Gracias por llamar. ¡Que tengas un gran día!",
    }
    response.say(final_goodbye.get(lang, final_goodbye['en']), voice=voice)
    response.hangup()
    
    save_conversation(call_sid)
    
    return str(response)


# ============================================================
# ROUTE: Call status tracking (REQUIRED by Twilio)
# ============================================================
@app.route("/call-status", methods=['POST', 'GET'])
def call_status():
    """Handle call status updates from Twilio"""
    call_sid = request.values.get('CallSid', 'Unknown')
    call_status = request.values.get('CallStatus', 'Unknown')
    
    print(f"\n📊 CALL STATUS UPDATE")
    print(f"Call ID: {call_sid}")
    print(f"Status: {call_status}")
    
    if call_status == 'completed' and call_sid in conversations:
        save_conversation(call_sid)
    
    return '', 200


# ============================================================
# FUNCTION: Save conversation
# ============================================================
def save_conversation(call_sid):
    """Save conversation to file"""
    if call_sid in conversations:
        conv = conversations[call_sid]
        conv['end_time'] = datetime.now().isoformat()
        
        os.makedirs('call_logs', exist_ok=True)
        
        filename = f"call_logs/{call_sid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(conv, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Conversation saved: {filename}")
        print(f"📊 Language: {kb.language_names[conv['language']]}, Messages: {len(conv['messages'])}")


# ============================================================
# ROUTE: Test endpoint
# ============================================================
@app.route("/test", methods=['GET'])
def test():
    return jsonify({
        'status': 'Server is running!',
        'llm_provider': 'groq',
        'knowledge_base': 'multilingual',
        'supported_languages': kb.supported_languages,
        'active_calls': len(conversations)
    })


# ============================================================
# START SERVER
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 MULTILINGUAL AI CALL CENTER")
    print("=" * 60)
    print(f"🌍 Supported Languages: {', '.join(kb.supported_languages)}")
    print(f"📞 LLM: Groq (Llama 3.3 70B)")
    print(f"🧠 Knowledge Base: Multilingual")
    print(f"🌐 Server: http://localhost:3000")
    print("=" * 60 + "\n")
    
    app.run(debug=True, port=3000, host='0.0.0.0')