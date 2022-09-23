import json
from collections import defaultdict
from time import sleep
from tts import create_mimic3_system, say_words

def main():
    mimic3 = create_mimic3_system(voice="en_UK/apope_low", preload_voices=["en_UK/apope_low"], rate=1)
    steno_data: dict = {}
    reverse_dict = defaultdict(set)

    with open("data/stened.json", "rb") as f:
        steno_data = json.load(f)

    for k, v in steno_data.items():
        reverse_dict[v].add(k)

    key_set = set(reverse_dict.keys())

    simple_words = []

    for word in key_set:
        new_word = word.replace('c', 'k').replace('ll', 'l')
        for val in reverse_dict[word]:
            steno = val.lower()
            # if len(val) == len(word) or len(val) == (len(word) - 1) or len(val) == (len(word) - 2):
            if new_word == steno:
                # print(word)
                # print(val)
                # print()
                simple_words.append((word, val))
            break

    #say_words("Can you do what I can do?", mimic3=mimic3, length_scale=3)

    sentence_data = [line.strip() for line in open("sentences.txt").readlines()]
    seconds_per_word = sentence_data[0]
    sentences = sentence_data[1:]

    ssml_data = []

    for words in sentences:
        ssml = " <break time='{seconds_per_word}s'/> ".join(words.split(" "))
        ssml = ssml.replace(",", ", comma,").replace("?", ", query?").replace(".", ", period.")
        ssml = ssml.format(seconds_per_word=seconds_per_word)
        ssml_data.append(f"<s>{ssml}</s>")

    print(ssml_data)

    speech = """
        <speak>
            <voice name="en_UK/apope_low">
                <prosody rate="0.6">""" + "<break time='1s'/>".join(ssml_data) + """
                </prosody>
            </voice>
        </speak>
    """
    say_words(speech, mimic3=mimic3, ssml=True)

    # say_words("""<speak>
    # <voice name="en_US/cmu-arctic_low">
    #   <prosody rate="0.4">
    #       <s>Can <break time="2s"/> you <break time="2s"/> hear me <break time="2s"/> now, query?</s>
    #   </prosody>
    # </voice>
  # </speak>""",mimic3=mimic3, ssml=True)
    return
    print(len(simple_words))
    count = 0
    for (word, sten) in simple_words:
        print("Saying: " + word + ": " + sten)
        say_words(word.capitalize() + ".", mimic3=mimic3)
        sleep(3)
        if count > 3:
            break
        count += 1


if __name__ == "__main__":
    main()
