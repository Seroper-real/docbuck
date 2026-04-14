import logging

from chains.needle_picker_chain import NeedlePickerChain
from models import Picker
from tools.cortex import Cortex


class Agent:

    def __init__(self):
        self.cortex = Cortex()
        self.needle_picker_chain = NeedlePickerChain()

    def start_chatting(self):
        logging.info("You can start chatting!")
        while True:
            user_input = input("\nTu: ").strip()
            if user_input.lower() in ['exit', 'quit']:
                break
            if not user_input:
                continue
            self.chat(user_input)

    def chat(self, prompt:str):
        picker : Picker = self.cortex.chain_picker(prompt)
        logging.debug(f"Picker: {picker}")
        if picker.selected == "Needle Picker Chain":
            print(self.needle_picker_chain.query(prompt))
        else:
            logging.info(f"Picker: {picker}")