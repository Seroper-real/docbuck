import logging

from chains.chain import Chain
from chains.needle_picker_chain import NeedlePickerChain
from models import Picker
from tools.cortex import Cortex


class Agent:

    #TODO:
    # - **Summary Chain**: Use for condensing one or more documents into main ideas.
    # - **Aggregation Chain**: Use for calculating, comparing, or synthesizing data across multiple sources.

    def __init__(self):
        self.cortex = Cortex()
        self.chains : dict[str, Chain] = {
            NeedlePickerChain.name: NeedlePickerChain(),
            #TODO add here all chains
        }


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
        picker : Picker = self.cortex.chain_picker(list(self.chains.values()), prompt)
        logging.debug(f"Picker: {picker}")
        chain = self.chains.get(picker.selected)
        if chain is None:
            logging.warning(f"Chain {picker.selected} not found")
            return
        print(chain.query(prompt))