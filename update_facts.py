import json

with open("data/external_facts.json", "r") as f:
    facts = json.load(f)

tree_fact = {
    "question": "Which types of plants or tree species does GNDEC have in its campus? Can you name those species?",
    "answer": "GNDEC has an immensely diverse campus with a variety of tree species performing a variety of functions. According to the Green Audit Report, there are over 2,010 trees of 87 species planted. Some prominent species include Ashoka, Mango, Alstonia, Crape jasmine, Christmas Tree, Amla, Bahera, Gulmohar, Tun, Bottle Palm, Neem, Poplar, Safeda (Eucalyptus), Amaltas, Chakrasia, and Maulishree.\n\nIn addition, the 'Guru Nanak Sacred Forest' was established in October 2019 to commemorate the 550th Parkash Purab of Shri Guru Nanak Dev Ji. It contains 550 trees of 38 different varieties, including Arjun, Baheda, Simbal, Banyan, Desi Babool, Desi Mango, Dhak (Palash), Goolar, Harde, Jamun, Khejri, Mahua, Neem, Peepal, Pilkhan, Sheesham, Suhanjana, White Siris, Ber, Harshingar, Karanj, Khair, Lasora, Tota, Aak, Anar, Mehndi, Motia, Falsa, Karonda, Khatta, Ashvagandha, and Garna.",
    "section": "Campus & Environment",
    "source_file": "Green Audit Report",
    "doc_url": "https://gndec.ac.in"
}

facts.append(tree_fact)

with open("data/external_facts.json", "w") as f:
    json.dump(facts, f, indent=2)

