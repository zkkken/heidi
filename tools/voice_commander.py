"""
tools/voice_commander.py
Voice Control Interface

Requirements: pip install SpeechRecognition pyaudio
"""
import speech_recognition as sr
import sys
import os
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.rpa_automation import RPAWorkflow


def main():
    r = sr.Recognizer()
    mic = sr.Microphone()
    workflow = RPAWorkflow()

    print("🎤 Voice Commander Ready.")
    print("Commands: 'Start Batch', 'Single Patient', 'Deep Dive', 'Exit'")

    while True:
        try:
            with mic as source:
                r.adjust_for_ambient_noise(source)
                print("\nListening...")
                audio = r.listen(source, timeout=5, phrase_time_limit=5)

            text = r.recognize_google(audio).lower()
            print(f"🗣️  You said: '{text}'")

            if "batch" in text:
                print("✅ Executing Batch Mode...")
                deep = "deep" in text
                workflow.run_batch_mode(deep_dive=deep)

            elif "single" in text:
                print("✅ Executing Single Patient Mode...")
                deep = "deep" in text
                workflow.run_single_mode(deep_dive=deep)

            elif "deep dive" in text or "deep" in text:
                print("✅ Executing Single Mode with Deep Dive...")
                workflow.run_single_mode(deep_dive=True)

            elif "exit" in text or "stop" in text or "quit" in text:
                print("👋 Bye!")
                break

        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            print("Could not understand audio")
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
