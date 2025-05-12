# quiz_data.py - Pre-defined quiz questions for the Language Learning Quiz Application
"""
This file contains a comprehensive collection of quiz questions organized by language and difficulty level.
These questions are used when AI-generated questions are not available or as a fallback.

Each question includes:
- type: The type of question (multiple_choice, fill_blank, matching, etc.)
- question: The question text
- answer: The correct answer
- points: Points awarded for a correct answer
- time_limit: Time limit in seconds
- Additional fields specific to each question type
"""

QUIZ_DATA = {
    # Each language has questions organized by difficulty level (beginner, intermediate, advanced)
    # Questions are stored as lists of dictionaries with standardized formats
    "English": {
        "beginner": [
            {
                "type": "multiple_choice",
                "question": "What is the English word for 'libro'?",
                "options": ["Book", "Door", "Window", "Chair"],
                "answer": "Book",
                "points": 10,
                "time_limit": 30
            },
            {
                "type": "multiple_choice_image",
                "question": "Which picture shows 'apple'?",
                "options": ["🍎", "🐶", "🚗", "🏠"],
                "answer": "🍎",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "matching",
                "question": "Match the words to their translations",
                "pairs": [("Hola", "Hello"), ("Adiós", "Goodbye"), ("Gracias", "Thank you")],
                "shuffled": True,
                "points": 15,
                "time_limit": 45
            },
            {
                "type": "fill_blank",
                "question": "I ___ a student.",
                "answer": "am",
                "hint": "Verb 'to be' for 'I'",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "sentence_construction",
                "question": "Arrange these words to form a correct sentence",
                "words": ["like", "I", "ice cream"],
                "answer": "I like ice cream",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "multiple_choice",
                "question": "What is the opposite of 'hot'?",
                "options": ["Cold", "Warm", "Big", "Small"],
                "answer": "Cold",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "fill_blank",
                "question": "She ___ to school every day.",
                "answer": "goes",
                "hint": "Third person singular of 'go'",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "multiple_choice",
                "question": "Which is a color?",
                "options": ["Blue", "Dog", "House", "Run"],
                "answer": "Blue",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "matching",
                "question": "Match the opposites",
                "pairs": [("Big", "Small"), ("Hot", "Cold"), ("Fast", "Slow")],
                "shuffled": True,
                "points": 15,
                "time_limit": 40
            },
            {
                "type": "fill_blank",
                "question": "They ___ watching TV now.",
                "answer": "are",
                "hint": "Verb 'to be' for 'they'",
                "points": 10,
                "time_limit": 25
            }
        ],
        "intermediate": [
            {
                "type": "multiple_choice",
                "question": "Which sentence is correct?",
                "options": [
                    "She go to school",
                    "She goes to school",
                    "She going to school",
                    "She gone to school"
                ],
                "answer": "She goes to school",
                "points": 15,
                "time_limit": 25
            },
            {
                "type": "error_spotting",
                "question": "What's wrong with this sentence: 'She go to school everyday'",
                "options": [
                    "The verb 'go' should be 'goes'",
                    "'everyday' should be 'every day'",
                    "There should be a period at the end",
                    "Nothing is wrong"
                ],
                "answer": "The verb 'go' should be 'goes'",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "context_response",
                "question": "Someone says 'Thank you'. What would you reply?",
                "options": [
                    "You're welcome",
                    "Hello",
                    "Goodbye",
                    "I don't know"
                ],
                "answer": "You're welcome",
                "points": 15,
                "time_limit": 25
            },
            {
                "type": "fill_blank",
                "question": "If I ___ rich, I would buy a big house.",
                "answer": "were",
                "hint": "Conditional form of 'to be'",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "mini_dialogue",
                "question": "Complete the dialogue: A: 'How was your weekend?' B: '___'",
                "options": [
                    "It was great! I went hiking.",
                    "Yes, I like weekends.",
                    "No, thank you.",
                    "My name is John."
                ],
                "answer": "It was great! I went hiking.",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "grammar_application",
                "question": "Change to past tense: 'She eats breakfast'",
                "answer": "She ate breakfast",
                "hint": "Past tense of 'eat' is irregular",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "multiple_choice",
                "question": "Which phrase is correct?",
                "options": [
                    "I've been to Paris last year",
                    "I went to Paris last year",
                    "I go to Paris last year",
                    "I am going to Paris last year"
                ],
                "answer": "I went to Paris last year",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "phrase_completion",
                "question": "Complete the phrase: 'Could you please ___ the window?'",
                "options": ["open", "opened", "opening", "opens"],
                "answer": "open",
                "points": 15,
                "time_limit": 25
            },
            {
                "type": "multiple_choice",
                "question": "What's the meaning of 'to look forward to'?",
                "options": [
                    "To be excited about something in the future",
                    "To look ahead while walking",
                    "To search for something",
                    "To plan something"
                ],
                "answer": "To be excited about something in the future",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "sentence_construction",
                "question": "Arrange these words to form a correct question",
                "words": ["you", "do", "live", "where"],
                "answer": "where do you live",
                "points": 15,
                "time_limit": 35
            }
        ],
        "advanced": [
            {
                "type": "idiom_interpretation",
                "question": "What does 'hit the books' mean?",
                "options": [
                    "To study hard",
                    "To physically hit books",
                    "To buy books",
                    "To read casually"
                ],
                "answer": "To study hard",
                "points": 20,
                "time_limit": 35
            },
            {
                "type": "complex_rephrasing",
                "question": "Rephrase: 'Despite the rain, we went hiking'",
                "options": [
                    "Although it was raining, we went hiking",
                    "We went hiking because it was raining",
                    "We went hiking, so it rained",
                    "We went hiking until it rained"
                ],
                "answer": "Although it was raining, we went hiking",
                "points": 20,
                "time_limit": 40
            },
            {
                "type": "cultural_nuance",
                "question": "When would you say 'bless you' in English-speaking cultures?",
                "options": [
                    "When someone sneezes",
                    "When greeting someone",
                    "When saying goodbye",
                    "When someone gives you a gift"
                ],
                "answer": "When someone sneezes",
                "points": 20,
                "time_limit": 30
            },
            {
                "type": "news_headline",
                "question": "What does this headline imply: 'Stock Market Plunges as Recession Fears Grow'?",
                "options": [
                    "The economy might be heading toward a downturn",
                    "The stock market is doing well",
                    "People are buying more stocks",
                    "The recession is over"
                ],
                "answer": "The economy might be heading toward a downturn",
                "points": 20,
                "time_limit": 45
            },
            {
                "type": "debate_style",
                "question": "Argue for: 'School uniforms should be mandatory'",
                "options": [
                    "They promote equality and reduce social pressure about clothing",
                    "They limit students' freedom of expression",
                    "They are too expensive for families",
                    "They make students look boring"
                ],
                "answer": "They promote equality and reduce social pressure about clothing",
                "points": 20,
                "time_limit": 50
            },
            {
                "type": "idiom_interpretation",
                "question": "What does 'break a leg' mean?",
                "options": [
                    "Good luck",
                    "Injure yourself",
                    "Run away",
                    "Dance well"
                ],
                "answer": "Good luck",
                "points": 20,
                "time_limit": 35
            },
            {
                "type": "complex_rephrasing",
                "question": "Rephrase: 'He's too tired to go to the party'",
                "options": [
                    "He isn't energetic enough to attend the party",
                    "He doesn't like parties",
                    "He went to the party despite being tired",
                    "He's excited about the party"
                ],
                "answer": "He isn't energetic enough to attend the party",
                "points": 20,
                "time_limit": 40
            },
            {
                "type": "cultural_nuance",
                "question": "In American culture, what does giving a thumbs up generally mean?",
                "options": [
                    "Approval or agreement",
                    "Disapproval",
                    "A rude gesture",
                    "Asking for help"
                ],
                "answer": "Approval or agreement",
                "points": 20,
                "time_limit": 30
            },
            {
                "type": "idiom_interpretation",
                "question": "What does 'cost an arm and a leg' mean?",
                "options": [
                    "To be very expensive",
                    "To cause physical injury",
                    "To be very difficult",
                    "To require surgery"
                ],
                "answer": "To be very expensive",
                "points": 20,
                "time_limit": 35
            },
            {
                "type": "debate_style",
                "question": "Argue against: 'Social media is beneficial for society'",
                "options": [
                    "It can lead to addiction and mental health issues",
                    "It helps people stay connected",
                    "It provides access to information",
                    "It creates job opportunities"
                ],
                "answer": "It can lead to addiction and mental health issues",
                "points": 20,
                "time_limit": 50
            }
        ]
    },
    "Spanish": {
        "beginner": [
            {
                "type": "multiple_choice",
                "question": "How do you say 'hello' in Spanish?",
                "options": ["Hola", "Adiós", "Gracias", "Por favor"],
                "answer": "Hola",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "multiple_choice_image",
                "question": "Which picture shows 'perro' (dog)?",
                "options": ["🐶", "🐱", "🐭", "🐰"],
                "answer": "🐶",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "audio_recognition",
                "question": "Listen to the audio and select the correct translation",
                "audio_file": "spanish_gato.mp3",
                "options": ["cat", "dog", "house", "car"],
                "answer": "cat",
                "points": 15,
                "time_limit": 25
            },
            {
                "type": "fill_blank",
                "question": "Buenos ___ (Good morning)",
                "answer": "días",
                "hint": "The Spanish word for 'days'",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "matching",
                "question": "Match Spanish words with their English translations",
                "pairs": [("Agua", "Water"), ("Pan", "Bread"), ("Leche", "Milk")],
                "shuffled": True,
                "points": 15,
                "time_limit": 40
            },
            {
                "type": "multiple_choice",
                "question": "How do you say 'thank you' in Spanish?",
                "options": ["Gracias", "Por favor", "De nada", "Buenos días"],
                "answer": "Gracias",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "¿Cómo ___ llamas? (What's your name?)",
                "answer": "te",
                "hint": "Second person reflexive pronoun",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "multiple_choice",
                "question": "Which is the correct translation for 'apple'?",
                "options": ["Manzana", "Plátano", "Naranja", "Uva"],
                "answer": "Manzana",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "sentence_construction",
                "question": "Arrange these words to form a correct sentence",
                "words": ["yo", "hablo", "español"],
                "answer": "yo hablo español",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "multiple_choice",
                "question": "How do you say 'goodbye' in Spanish?",
                "options": ["Adiós", "Hola", "Gracias", "Buenos días"],
                "answer": "Adiós",
                "points": 10,
                "time_limit": 20
            }
        ],
        "intermediate": [
            {
                "type": "multiple_choice",
                "question": "How do you say 'I am hungry' in Spanish?",
                "options": [
                    "Tengo frío",
                    "Tengo hambre",
                    "Tengo sed",
                    "Tengo sueño"
                ],
                "answer": "Tengo hambre",
                "points": 15,
                "time_limit": 25
            },
            {
                "type": "error_spotting",
                "question": "What's wrong with this sentence: 'Yo soy estudiante en la universidad por 2 años'",
                "options": [
                    "Should use 'hace' instead of 'por'",
                    "Should use 'estoy' instead of 'soy'",
                    "Should use 'colegio' instead of 'universidad'",
                    "Nothing is wrong"
                ],
                "answer": "Should use 'hace' instead of 'por'",
                "points": 15,
                "time_limit": 35
            },
            {
                "type": "context_response",
                "question": "Someone says 'Gracias'. What would you reply?",
                "options": [
                    "De nada",
                    "Hola",
                    "Adiós",
                    "Buenos días"
                ],
                "answer": "De nada",
                "points": 15,
                "time_limit": 25
            },
            {
                "type": "fill_blank",
                "question": "Si yo ___ dinero, compraría una casa. (If I had money, I would buy a house)",
                "answer": "tuviera",
                "hint": "Subjunctive form of 'tener'",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "mini_dialogue",
                "question": "Complete the dialogue: A: '¿Qué hiciste ayer?' B: '___'",
                "options": [
                    "Fui al cine con mis amigos",
                    "Voy al cine mañana",
                    "No me gusta el cine",
                    "Me llamo Juan"
                ],
                "answer": "Fui al cine con mis amigos",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "grammar_application",
                "question": "Change to past tense: 'Ella come desayuno'",
                "answer": "Ella comió desayuno",
                "hint": "Preterite form of 'comer'",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "multiple_choice",
                "question": "Which is the correct form of the verb?",
                "options": [
                    "Yo hablo español",
                    "Yo hablas español",
                    "Yo habla español",
                    "Yo hablamos español"
                ],
                "answer": "Yo hablo español",
                "points": 15,
                "time_limit": 25
            },
            {
                "type": "phrase_completion",
                "question": "Complete the phrase: '¿Podrías ___ la ventana, por favor?'",
                "options": ["abrir", "abriendo", "abierto", "abre"],
                "answer": "abrir",
                "points": 15,
                "time_limit": 25
            },
            {
                "type": "multiple_choice",
                "question": "What's the meaning of 'tener ganas de'?",
                "options": [
                    "To feel like doing something",
                    "To be hungry",
                    "To be tired",
                    "To be thirsty"
                ],
                "answer": "To feel like doing something",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "sentence_construction",
                "question": "Arrange these words to form a correct question",
                "words": ["vives", "dónde", "tú"],
                "answer": "dónde vives tú",
                "points": 15,
                "time_limit": 35
            }
        ],
        "advanced": [
            {
                "type": "idiom_interpretation",
                "question": "What does 'estar en las nubes' mean?",
                "options": [
                    "To be daydreaming",
                    "To be flying in an airplane",
                    "To be very happy",
                    "To be in a difficult situation"
                ],
                "answer": "To be daydreaming",
                "points": 20,
                "time_limit": 35
            },
            {
                "type": "complex_rephrasing",
                "question": "Rephrase: 'A pesar de la lluvia, fuimos de excursión'",
                "options": [
                    "Aunque llovía, fuimos de excursión",
                    "Fuimos de excursión porque llovía",
                    "Fuimos de excursión, así que llovió",
                    "Fuimos de excursión hasta que llovió"
                ],
                "answer": "Aunque llovía, fuimos de excursión",
                "points": 20,
                "time_limit": 40
            },
            {
                "type": "cultural_nuance",
                "question": "In Spanish-speaking cultures, what is a 'siesta'?",
                "options": [
                    "A short nap taken in the early afternoon",
                    "A traditional dance",
                    "A type of food",
                    "A religious ceremony"
                ],
                "answer": "A short nap taken in the early afternoon",
                "points": 20,
                "time_limit": 30
            },
            {
                "type": "idiom_interpretation",
                "question": "What does 'costar un ojo de la cara' mean?",
                "options": [
                    "To be very expensive",
                    "To be very difficult",
                    "To be very painful",
                    "To be very far away"
                ],
                "answer": "To be very expensive",
                "points": 20,
                "time_limit": 35
            },
            {
                "type": "debate_style",
                "question": "Argue for: 'El aprendizaje de idiomas debería ser obligatorio en las escuelas'",
                "options": [
                    "Abre oportunidades profesionales y culturales",
                    "Es demasiado difícil para algunos estudiantes",
                    "No todos los estudiantes lo necesitarán",
                    "Hay materias más importantes"
                ],
                "answer": "Abre oportunidades profesionales y culturales",
                "points": 20,
                "time_limit": 50
            },
            {
                "type": "news_headline",
                "question": "What does this headline imply: 'España enfrenta su peor sequía en décadas'?",
                "options": [
                    "Spain is experiencing a severe water shortage",
                    "Spain is having great weather",
                    "Spain is producing more crops than ever",
                    "Spain is experiencing heavy rainfall"
                ],
                "answer": "Spain is experiencing a severe water shortage",
                "points": 20,
                "time_limit": 45
            },
            {
                "type": "cultural_nuance",
                "question": "What is 'el Día de los Muertos'?",
                "options": [
                    "A celebration honoring deceased loved ones",
                    "A scary holiday similar to Halloween",
                    "A day of mourning when people wear black",
                    "The Spanish name for Halloween"
                ],
                "answer": "A celebration honoring deceased loved ones",
                "points": 20,
                "time_limit": 35
            },
            {
                "type": "complex_rephrasing",
                "question": "Rephrase: 'Está demasiado cansado para ir a la fiesta'",
                "options": [
                    "No tiene suficiente energía para asistir a la fiesta",
                    "No le gustan las fiestas",
                    "Fue a la fiesta a pesar de estar cansado",
                    "Está emocionado por la fiesta"
                ],
                "answer": "No tiene suficiente energía para asistir a la fiesta",
                "points": 20,
                "time_limit": 40
            },
            {
                "type": "idiom_interpretation",
                "question": "What does 'meter la pata' mean?",
                "options": [
                    "To make a mistake",
                    "To put your foot in water",
                    "To walk quickly",
                    "To kick something"
                ],
                "answer": "To make a mistake",
                "points": 20,
                "time_limit": 35
            },
            {
                "type": "debate_style",
                "question": "Argue against: 'Las redes sociales son beneficiosas para la sociedad'",
                "options": [
                    "Pueden causar adicción y problemas de salud mental",
                    "Ayudan a las personas a mantenerse conectadas",
                    "Proporcionan acceso a información",
                    "Crean oportunidades de trabajo"
                ],
                "answer": "Pueden causar adicción y problemas de salud mental",
                "points": 20,
                "time_limit": 50
            }
        ]
    },
    "Chinese": {
        "beginner": [
            {
                "type": "multiple_choice",
                "question": "How do you say 'hello' in Chinese?",
                "options": ["你好 (Nǐ hǎo)", "谢谢 (Xièxiè)", "再见 (Zàijiàn)", "对不起 (Duìbùqǐ)"],
                "answer": "你好 (Nǐ hǎo)",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "multiple_choice_image",
                "question": "Which picture shows '狗' (dog)?",
                "options": ["🐶", "🐱", "🐭", "🐰"],
                "answer": "🐶",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "我 ___ 学生 (I am a student)",
                "answer": "是",
                "hint": "The Chinese verb 'to be'",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "matching",
                "question": "Match Chinese words with their English translations",
                "pairs": [("水", "Water"), ("面包", "Bread"), ("牛奶", "Milk")],
                "shuffled": True,
                "points": 15,
                "time_limit": 40
            },
            {
                "type": "multiple_choice",
                "question": "How do you say 'thank you' in Chinese?",
                "options": ["谢谢 (Xièxiè)", "对不起 (Duìbùqǐ)", "不客气 (Bù kèqì)", "早上好 (Zǎoshang hǎo)"],
                "answer": "谢谢 (Xièxiè)",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "你 ___ 什么名字？ (What's your name?)",
                "answer": "叫",
                "hint": "The verb 'to be called'",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "multiple_choice",
                "question": "Which is the correct translation for 'apple'?",
                "options": ["苹果 (Píngguǒ)", "香蕉 (Xiāngjiāo)", "橙子 (Chéngzi)", "葡萄 (Pútáo)"],
                "answer": "苹果 (Píngguǒ)",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "sentence_construction",
                "question": "Arrange these words to form a correct sentence",
                "words": ["我", "喜欢", "中文"],
                "answer": "我喜欢中文",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "multiple_choice",
                "question": "How do you say 'goodbye' in Chinese?",
                "options": ["再见 (Zàijiàn)", "你好 (Nǐ hǎo)", "谢谢 (Xièxiè)", "早上好 (Zǎoshang hǎo)"],
                "answer": "再见 (Zàijiàn)",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "一, 二, ___, 四, 五 (One, two, ___, four, five)",
                "answer": "三",
                "hint": "The number between '二' and '四'",
                "points": 10,
                "time_limit": 20
            }
        ],
        "intermediate": [
            {
                "type": "multiple_choice",
                "question": "How do you say 'I am hungry' in Chinese?",
                "options": [
                    "我饿了 (Wǒ è le)",
                    "我冷 (Wǒ lěng)",
                    "我渴 (Wǒ kě)",
                    "我累 (Wǒ lèi)"
                ],
                "answer": "我饿了 (Wǒ è le)",
                "points": 15,
                "time_limit": 25
            }
        ]
    },
    "Malay": {
        "beginner": [
            {
                "type": "multiple_choice",
                "question": "How do you say 'hello' in Malay?",
                "options": ["Hai", "Selamat tinggal", "Terima kasih", "Maaf"],
                "answer": "Hai",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "multiple_choice_image",
                "question": "Which picture shows 'anjing' (dog)?",
                "options": ["🐶", "🐱", "🐭", "🐰"],
                "answer": "🐶",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "Saya ___ seorang pelajar (I am a student)",
                "answer": "adalah",
                "hint": "The Malay verb 'to be'",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "matching",
                "question": "Match Malay words with their English translations",
                "pairs": [("Air", "Water"), ("Roti", "Bread"), ("Susu", "Milk")],
                "shuffled": True,
                "points": 15,
                "time_limit": 40
            },
            {
                "type": "multiple_choice",
                "question": "How do you say 'thank you' in Malay?",
                "options": ["Terima kasih", "Maaf", "Sama-sama", "Selamat pagi"],
                "answer": "Terima kasih",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "Siapa ___ anda? (What's your name?)",
                "answer": "nama",
                "hint": "The Malay word for 'name'",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "multiple_choice",
                "question": "Which is the correct translation for 'apple'?",
                "options": ["Epal", "Pisang", "Oren", "Anggur"],
                "answer": "Epal",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "sentence_construction",
                "question": "Arrange these words to form a correct sentence",
                "words": ["Saya", "suka", "bahasa Melayu"],
                "answer": "Saya suka bahasa Melayu",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "multiple_choice",
                "question": "How do you say 'goodbye' in Malay?",
                "options": ["Selamat tinggal", "Hai", "Terima kasih", "Selamat pagi"],
                "answer": "Selamat tinggal",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "Satu, dua, ___, empat, lima (One, two, ___, four, five)",
                "answer": "tiga",
                "hint": "The number between 'dua' and 'empat'",
                "points": 10,
                "time_limit": 20
            }
        ],
        "intermediate": [
            {
                "type": "multiple_choice",
                "question": "How do you say 'I am hungry' in Malay?",
                "options": [
                    "Saya lapar",
                    "Saya sejuk",
                    "Saya haus",
                    "Saya penat"
                ],
                "answer": "Saya lapar",
                "points": 15,
                "time_limit": 25
            }
        ]
    },
    "Tamil": {
        "beginner": [
            {
                "type": "multiple_choice",
                "question": "How do you say 'hello' in Tamil?",
                "options": ["வணக்கம் (Vanakkam)", "நன்றி (Nandri)", "பிறகு பார்க்கலாம் (Piragu Parkalam)", "மன்னிக்கவும் (Mannikkavum)"],
                "answer": "வணக்கம் (Vanakkam)",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "multiple_choice_image",
                "question": "Which picture shows 'நாய்' (dog)?",
                "options": ["🐶", "🐱", "🐭", "🐰"],
                "answer": "🐶",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "நான் ஒரு மாணவன் ___ (I am a student)",
                "answer": "ஆவேன்",
                "hint": "The Tamil verb 'to be'",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "matching",
                "question": "Match Tamil words with their English translations",
                "pairs": [("தண்ணீர்", "Water"), ("ரொட்டி", "Bread"), ("பால்", "Milk")],
                "shuffled": True,
                "points": 15,
                "time_limit": 40
            },
            {
                "type": "multiple_choice",
                "question": "How do you say 'thank you' in Tamil?",
                "options": ["நன்றி (Nandri)", "மன்னிக்கவும் (Mannikkavum)", "வரவேற்கிறேன் (Varaverkirren)", "காலை வணக்கம் (Kalai Vanakkam)"],
                "answer": "நன்றி (Nandri)",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "உங்கள் ___ என்ன? (What's your name?)",
                "answer": "பெயர்",
                "hint": "The Tamil word for 'name'",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "multiple_choice",
                "question": "Which is the correct translation for 'apple'?",
                "options": ["ஆப்பிள்", "வாழைப்பழம்", "ஆரஞ்சு", "திராட்சை"],
                "answer": "ஆப்பிள்",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "sentence_construction",
                "question": "Arrange these words to form a correct sentence",
                "words": ["நான்", "தமிழ்", "விரும்புகிறேன்"],
                "answer": "நான் தமிழ் விரும்புகிறேன்",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "multiple_choice",
                "question": "How do you say 'goodbye' in Tamil?",
                "options": ["பிறகு பார்க்கலாம் (Piragu Parkalam)", "வணக்கம் (Vanakkam)", "நன்றி (Nandri)", "காலை வணக்கம் (Kalai Vanakkam)"],
                "answer": "பிறகு பார்க்கலாம் (Piragu Parkalam)",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "ஒன்று, இரண்டு, ___, நான்கு, ஐந்து (One, two, ___, four, five)",
                "answer": "மூன்று",
                "hint": "The number between 'இரண்டு' and 'நான்கு'",
                "points": 10,
                "time_limit": 20
            }
        ],
        "intermediate": [
            {
                "type": "multiple_choice",
                "question": "How do you say 'I am hungry' in Tamil?",
                "options": [
                    "எனக்கு பசிக்கிறது",
                    "எனக்கு குளிராக இருக்கிறது",
                    "எனக்கு தாகமாக இருக்கிறது",
                    "எனக்கு சோர்வாக இருக்கிறது"
                ],
                "answer": "எனக்கு பசிக்கிறது",
                "points": 15,
                "time_limit": 25
            }
        ]
    },
    "French": {
        "beginner": [
            {
                "type": "multiple_choice",
                "question": "How do you say 'hello' in French?",
                "options": ["Bonjour", "Au revoir", "Merci", "S'il vous plaît"],
                "answer": "Bonjour",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "multiple_choice_image",
                "question": "Which picture shows 'chien' (dog)?",
                "options": ["🐶", "🐱", "🐭", "🐰"],
                "answer": "🐶",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "Comment ___ -vous? (How are you?)",
                "answer": "allez",
                "hint": "From the verb 'aller' (to go)",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "matching",
                "question": "Match French words with their English translations",
                "pairs": [("Eau", "Water"), ("Pain", "Bread"), ("Lait", "Milk")],
                "shuffled": True,
                "points": 15,
                "time_limit": 40
            },
            {
                "type": "multiple_choice",
                "question": "How do you say 'thank you' in French?",
                "options": ["Merci", "S'il vous plaît", "De rien", "Bonjour"],
                "answer": "Merci",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "Je m'___ Jean. (My name is Jean.)",
                "answer": "appelle",
                "hint": "From the verb 's'appeler' (to call oneself)",
                "points": 10,
                "time_limit": 25
            },
            {
                "type": "multiple_choice",
                "question": "Which is the correct translation for 'apple'?",
                "options": ["Pomme", "Banane", "Orange", "Raisin"],
                "answer": "Pomme",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "sentence_construction",
                "question": "Arrange these words to form a correct sentence",
                "words": ["je", "parle", "français"],
                "answer": "je parle français",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "multiple_choice",
                "question": "How do you say 'goodbye' in French?",
                "options": ["Au revoir", "Bonjour", "Merci", "Bonsoir"],
                "answer": "Au revoir",
                "points": 10,
                "time_limit": 20
            },
            {
                "type": "fill_blank",
                "question": "Un, deux, ___, quatre, cinq. (One, two, ___, four, five.)",
                "answer": "trois",
                "hint": "The number between 'deux' and 'quatre'",
                "points": 10,
                "time_limit": 20
            }
        ],
        "intermediate": [
            {
                "type": "multiple_choice",
                "question": "How do you say 'I am hungry' in French?",
                "options": [
                    "J'ai faim",
                    "J'ai froid",
                    "J'ai soif",
                    "J'ai sommeil"
                ],
                "answer": "J'ai faim",
                "points": 15,
                "time_limit": 25
            },
            {
                "type": "error_spotting",
                "question": "What's wrong with this sentence: 'Je suis étudiant à l'université pour 2 ans'",
                "options": [
                    "Should use 'depuis' instead of 'pour'",
                    "Should use 'je suis' instead of 'j'ai'",
                    "Should use 'école' instead of 'université'",
                    "Nothing is wrong"
                ],
                "answer": "Should use 'depuis' instead of 'pour'",
                "points": 15,
                "time_limit": 35
            },
            {
                "type": "context_response",
                "question": "Someone says 'Merci'. What would you reply?",
                "options": [
                    "De rien",
                    "Bonjour",
                    "Au revoir",
                    "Bonsoir"
                ],
                "answer": "De rien",
                "points": 15,
                "time_limit": 25
            },
            {
                "type": "fill_blank",
                "question": "Si j'___ de l'argent, j'achèterais une maison. (If I had money, I would buy a house)",
                "answer": "avais",
                "hint": "Imperfect form of 'avoir'",
                "points": 15,
                "time_limit": 30
            },
            {
                "type": "mini_dialogue",
                "question": "Complete the dialogue: A: 'Comment s'est passé ton weekend?' B: '___'",
                "options": [
                    "C'était super! Je suis allé au cinéma",
                    "Je vais au cinéma demain",
                    "Je n'aime pas le cinéma",
                    "Je m'appelle Jean"
                ],
                "answer": "C'était super! Je suis allé au cinéma",
                "points": 15,
                "time_limit": 30
            }
        ]
    }
}
