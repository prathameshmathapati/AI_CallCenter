from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

conversations = {}

@app.route("/answer", methods=['GET', 'POST'])
def answer_call():
    caller = request.values.get('From', 'Unknown')
    call_sid = request.values.get('CallSid', 'Unknown')
    
    print("="*60)
    print(f"📞 INCOMING CALL")
    print(f"From: {caller}")
    print(f"Call ID: {call_sid}")
    print("="*60)
    
    try:
        response = VoiceResponse()
        
        # Simple greeting
        response.say(
            "Hello! This is your A I assistant. I am working correctly. How can I help you today?",
            voice='Polly.Joanna',
            language='en-US'
        )
        
        response.pause(length=1)
        
        # Listen for speech
        gather = Gather(
            input='speech',
            action='/process-speech',
            timeout=5,
            language='en-US'
        )
        gather.say("Please tell me your question.", voice='Polly.Joanna')
        response.append(gather)
        
        # Fallback
        response.say("Thank you for calling. Goodbye!", voice='Polly.Joanna')
        response.hangup()
        
        print("✅ Sent TwiML response successfully")
        return str(response)
        
    except Exception as e:
        print(f"❌ ERROR in /answer: {e}")
        response = VoiceResponse()
        response.say("I apologize, there was an error. Goodbye.", voice='Polly.Joanna')
        return str(response)


@app.route("/process-speech", methods=['POST'])
def process_speech():
    user_speech = request.values.get('SpeechResult', '')
    call_sid = request.values.get('CallSid', 'Unknown')
    
    print("="*60)
    print(f"💬 CUSTOMER SAID: {user_speech}")
    print(f"Call ID: {call_sid}")
    print("="*60)
    
    try:
        response = VoiceResponse()
        
        if not user_speech:
            response.say("I didn't catch that.", voice='Polly.Joanna')
        elif 'bye' in user_speech.lower():
            response.say("Thank you for calling! Goodbye!", voice='Polly.Joanna')
            response.hangup()
            return str(response)
        else:
            response.say(f"You said: {user_speech}. I am a simple test assistant.", voice='Polly.Joanna')
        
        response.pause(length=1)
        
        gather = Gather(
            input='speech',
            action='/process-speech',
            timeout=5,
            language='en-US'
        )
        gather.say("Anything else?", voice='Polly.Joanna')
        response.append(gather)
        
        response.say("Thank you! Goodbye!", voice='Polly.Joanna')
        response.hangup()
        
        print("✅ Processed speech successfully")
        return str(response)
        
    except Exception as e:
        print(f"❌ ERROR in /process-speech: {e}")
        response = VoiceResponse()
        response.say("Error processing speech. Goodbye.", voice='Polly.Joanna')
        return str(response)


@app.route("/call-status", methods=['POST', 'GET'])
def call_status():
    """Handle call status updates from Twilio"""
    call_sid = request.values.get('CallSid', 'Unknown')
    call_status = request.values.get('CallStatus', 'Unknown')
    
    print(f"📊 Call Status: {call_status} (Call ID: {call_sid})")
    
    return '', 200  # Return empty 200 OK response


@app.route("/test", methods=['GET'])
def test():
    return {"status": "Minimal server running!", "version": "minimal-test"}


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 MINIMAL TEST SERVER")
    print("="*60)
    print("Server: http://localhost:3000")
    print("This is a simplified version for debugging")
    print("="*60 + "\n")
    
    app.run(debug=True, port=3000, host='0.0.0.0')