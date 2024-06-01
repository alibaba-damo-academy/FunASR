"""
  Copyright FunASR (https://github.com/alibaba-damo-academy/FunASR). All Rights
  Reserved. MIT License  (https://opensource.org/licenses/MIT)
  
  2023-2024 by zhaomingwork@qq.com  
"""

from funasr_api import FunasrApi
import wave

def recognizer_example():
    # create an recognizer
    rcg = FunasrApi(
        uri="wss://www.funasr.com:10096/"
    )
    text=rcg.rec_file("asr_example.mp3")
    print("asr_example.mp3 text=",text)

def recognizer_stream_example():
    #define call_back function for msg 
    def on_msg(msg):
       print("stream_example msg=",msg)
    rcg = FunasrApi(
        uri="wss://www.funasr.com:10096/",msg_callback=on_msg
    )
    rcg.create_connection()
    
    wav_path = "asr_example.wav"

    with open(wav_path, "rb") as f:
        audio_bytes = f.read()
        
    # use FunasrApi's audio2wav to covert other audio to PCM if needed
    #import os
    #file_ext=os.path.splitext(wav_path)[-1].upper()
    #if not file_ext =="PCM" and not file_ext =="WAV":
    #       audio_bytes=rcg.audio2wav(audio_bytes)
    
    stride = int(60 * 10 / 10 / 1000 * 16000 * 2)
    chunk_num = (len(audio_bytes) - 1) // stride + 1

    for i in range(chunk_num):

        beg = i * stride
        data = audio_bytes[beg : beg + stride]

        rcg.feed_chunk(data)
    msg=rcg.get_result()
    print("asr_example.wav text=",msg)
    
    
if __name__ == "__main__":

    print("example for Funasr_websocket_recognizer")
 
    recognizer_stream_example()

    recognizer_example()
    
    

