from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_bcrypt import Bcrypt
from flask import request, jsonify
from dotenv import load_dotenv
load_dotenv()
import os
import mysql.connector
import openai
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this later

# Initialize extensions
bcrypt = Bcrypt(app)

# Connect to MySQL
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)
cursor = db.cursor(dictionary=True)


# --- Routes ---

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/favicon.ico')
def favicon():
    return '', 204  # Returns no content, effectively ignoring the request


from flask import session

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user['password'], password):
            # Set session for user ID
            session['user_id'] = user['id']
            print(f"User ID saved to session: {session['user_id']}")  # Debug print
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password.'})

    return render_template('login.html')

def get_user_from_db():
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to view your profile.', 'warning')
        return redirect(url_for('login'))

    cursor.execute("SELECT first_name, last_name, gender, id FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if user:
        return user
    else:
        return None



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        birth_day = request.form['birth_day']
        birth_month = request.form['birth_month']
        birth_year = request.form['birth_year']
        gender = request.form['gender']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        try:
            cursor = db.cursor()

            # Check if username already exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('Username already exists.', 'danger')
                cursor.close()
                return redirect(url_for('register'))

            # Hash the password
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

            # Insert new user
            cursor.execute("""
                INSERT INTO users 
                (username, first_name, last_name, birth_day, birth_month, birth_year, gender, password)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (username, first_name, last_name, birth_day, birth_month, birth_year, gender, hashed_pw))

            # Get new user_id
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id = cursor.fetchone()[0]

            # Insert default skin
            cursor.execute("""
                INSERT INTO user_skins (user_id, skin_code, map, claimed, equipped)
                VALUES (%s, 'default', NULL, 1, 1)
            """, (user_id,))

            # Insert default progress for all maps
            maps = [
                'multiplication',
                'addition',
                'subtraction',
                'division',
                'counting',
                'comparison',
                'numerals',
                'placevalue'
            ]

            for map_name in maps:
                cursor.execute("""
                    INSERT INTO user_game_progress (user_id, map, stage_key, correct, wrong, total, difficulty)
                    VALUES (%s, %s, '1', 0, 0, 0, 'easy')
                """, (user_id, map_name))

            # Commit all changes
            db.commit()
            cursor.close()

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            db.rollback()
            print(f"[Registration Error] {e}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')





# 🔥 OpenRouter Setup
openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key = "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"  # ← Replace this with your OpenRouter API Key



allowed_interactions = {
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
    "thank you", "thanks", "ty", "ok", "okay", "yes", "no", "sure", "alright"
}

math_keywords = [
    "add", "addition", "plus",
    "subtract", "subtraction", "minus",
    "multiply", "multiplication", "times",
    "divide", "division",
    "count", "number", "place value", "roman numeral", "compare",
    "greater than", "less than", "equal",
    "word problem", "how many", "left", "more", "fewer",
    "counting forward", "skip counting", "counting backwards",
    "borrowing", "regrouping", "long division",
    "reading roman numerals", "converting roman numerals",
    "ones", "tens", "hundreds", "thousands", "ten thousands"
]

yes_responses = {"yes", "yeah", "yep", "sure", "more help", "help"}
no_responses = {"no", "nah", "nope", "stop"}

def is_math_question(message: str) -> bool:
    has_number = bool(re.search(r'\d', message))
    has_keyword = any(k in message for k in math_keywords)
    return has_number or has_keyword

def compute_answer(question: str):
    try:
        numbers = list(map(float, re.findall(r'\d+', question)))
        if len(numbers) < 2:
            return None

        if any(op in question for op in ["add", "plus", "+"]):
            return int(numbers[0] + numbers[1])
        elif any(op in question for op in ["subtract", "minus", "-"]):
            return int(numbers[0] - numbers[1])
        elif any(op in question for op in ["multiply", "times", "*"]):
            return int(numbers[0] * numbers[1])
        elif any(op in question for op in ["divide", "division", "/"]):
            if numbers[1] == 0:
                return None
            return int(numbers[0] / numbers[1])
        else:
            return None
    except:
        return None

def check_answer(user_answer: str, expected_answer) -> bool:
    try:
        return int(user_answer) == int(expected_answer)
    except:
        return False

@app.route('/chatbot-api', methods=['POST'])
def chatbot_api():
    data = request.json
    user_message = data.get("message", "").strip().lower()

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Initialize session variables if missing
    if 'last_question' not in session:
        session['last_question'] = ""
    if 'step' not in session:
        session['step'] = 0
    if 'expected_answer' not in session:
        session['expected_answer'] = None

    # Step 0: Greeting or math question detection
    if session['step'] == 0:
        if user_message in allowed_interactions:
            friendly_responses = {
                "hello": "Hello! I'm Counticus, your friendly math helper!",
                "hi": "Hi there! Ready to do some math?",
                "hey": "Hey! I'm here if you need help with math.",
                "good morning": "Good morning! I'm here to help with math problems.",
                "good afternoon": "Good afternoon! Ready to learn some math?",
                "good evening": "Good evening! Counticus at your service!",
                "thank you": "You're welcome!",
                "thanks": "No problem!",
                "ty": "You're welcome!",
                "ok": "Okay!",
                "okay": "Okay!",
                "sure": "Okay! Just send me a math question when you're ready.",
                "alright": "Alright! I'm here when you need help."
            }
            return jsonify({"reply": friendly_responses.get(user_message, "I'm here to help with math!")})

        if not is_math_question(user_message):
            return jsonify({"reply": "Sorry, I can only help with math questions or respond to simple greetings!"})

        # Save question and expected answer, then move to step 1
        session['last_question'] = user_message
        session['expected_answer'] = compute_answer(user_message)
        session['step'] = 1

    # Step 1: Give simple tip and ask if user wants more help
    if session['step'] == 1:
        if user_message in yes_responses:
            session['step'] = 2
        elif user_message in no_responses:
            session['step'] = 0
            session['last_question'] = ""
            session['expected_answer'] = None
            return jsonify({"reply": "Alright! Let me know if you have another math question."})
        else:
            # Generate tip from OpenAI
            tip_prompt = f"Give a simple tip to solve this math problem without giving the answer: '{session['last_question']}'. End by asking: 'Would you like more help?' Keep it short and friendly for Grade 1."
            try:
                system_prompt = "You are Counticus, a friendly Grade 1 math tutor."
                response = openai.ChatCompletion.create(
                    model="mistralai/mistral-7b-instruct:free",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": tip_prompt}
                    ]
                )
                reply = response['choices'][0]['message']['content']
                return jsonify({"reply": reply})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    # Step 2: Provide step-by-step solution without final answer, then ask for user's answer
    if session['step'] == 2:
        step_prompt = f"Give a step-by-step solution without the final answer for this math problem: '{session['last_question']}'. Then ask: 'What do you think the answer is?' Keep it short and friendly for Grade 1."
        try:
            system_prompt = "You are Counticus, a friendly Grade 1 math tutor."
            response = openai.ChatCompletion.create(
                model="mistralai/mistral-7b-instruct:free",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": step_prompt}
                ]
            )
            reply = response['choices'][0]['message']['content']
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        session['step'] = 2.5
        return jsonify({"reply": reply})

    # Step 2.5: Check user's answer, if correct reset else ask if want full explanation
    if session['step'] == 2.5:
        expected = session.get('expected_answer')
        if expected is None:
            # If we can't compute expected answer, skip to step 3
            session['step'] = 3
        else:
            if check_answer(user_message, expected):
                session['step'] = 0
                session['last_question'] = ""
                session['expected_answer'] = None
                return jsonify({"reply": "That's correct! Great job! 🎉 Let me know if you want to try another question."})
            else:
                session['step'] = 3
                return jsonify({"reply": "That's not quite right. Would you like me to explain the full solution?"})

    # Step 3: Give full solution with final answer or end
    if session['step'] == 3:
        if user_message in yes_responses:
            full_prompt = f"Give a full step-by-step solution including the final answer for this math problem: '{session['last_question']}'. Keep it short and friendly for Grade 1."
            try:
                system_prompt = "You are Counticus, a friendly Grade 1 math tutor."
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_prompt}
                    ]
                )
                reply = response['choices'][0]['message']['content']
            except Exception as e:
                return jsonify({"error": str(e)}), 500

            session['step'] = 0
            session['last_question'] = ""
            session['expected_answer'] = None
            return jsonify({"reply": reply})

        elif user_message in no_responses:
            session['step'] = 0
            session['last_question'] = ""
            session['expected_answer'] = None
            return jsonify({"reply": "Okay! Feel free to ask me another math question anytime."})

        else:
            return jsonify({"reply": "Sorry, your answer is not valid please reply with 'yes' or 'no' if you want the full explanation."})

    # Default fallback
    return jsonify({"reply": "Sorry, I didn't understand that. Please ask a math question or say hello!"})




@app.route('/reset-chat-session', methods=['POST'])
def reset_chat_session():
    session.pop('last_question', None)
    session.pop('step', None)
    session.pop('expected_answer', None)
    return jsonify({"message": "Chat session reset"})



@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/stages')
def stages():
    # Retrieve the selected map from the URL query parameters
    selected_map = request.args.get('map', None)  # Get the selected map (e.g., multiplication)
    selected_stage = request.args.get('stage', '1')  # Default to stage 1 if no stage is specified
    return render_template('stages.html', selected_map=selected_map, selected_stage=selected_stage)

@app.route('/dashboard')
def dashboard():
    user = get_user_from_db()  # Fetch user from database
    if not user:
        flash('User not found or not logged in.', 'danger')
        return redirect(url_for('login'))
    
    # Pass first_name, last_name, and gender to the template
    return render_template('dashboard.html', first_name=user['first_name'], 
                           last_name=user['last_name'], gender=user['gender'], id=user ['id'])



@app.route('/roadmap')
def roadmap():
    return render_template('roadmap.html')

@app.route('/shop')
def shop():
    return render_template('shop.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

import json
from flask import redirect, session, render_template

@app.route('/collectibles')
def collectibles():
    user_id = session.get('user_id')  # Get user_id from session or other source

    if not user_id:
        # Redirect to login or show error if user not logged in
        return redirect('/login')

    try:
        cursor = db.cursor()
        cursor.execute("SELECT skin_code FROM user_skins WHERE user_id = %s AND claimed = 1", (user_id,))
        claimed_skins = cursor.fetchall()
        claimed_skin_ids = [skin[0] for skin in claimed_skins]

        # Debugging outputs
        print("Claimed skins from DB:", claimed_skins)
        print("Claimed skin IDs:", claimed_skin_ids)

        cursor.close()
    except Exception as e:
        print("Error fetching skins:", e)
        claimed_skin_ids = []

    # Convert to JSON for passing to JavaScript
    claimed_skin_ids_json = json.dumps(claimed_skin_ids)

    return render_template('collectibles.html', claimed_skin_ids_json=claimed_skin_ids_json)







@app.route('/monster_atlas')
def monster_atlas():
    return render_template('monster_atlas.html')

@app.route('/logout')
def logout():
    return redirect(url_for('login'))


@app.route('/game', methods=['GET'])
def game():
    user_id = 1  # Hardcoded user ID

    # Get selected map and stage from query parameters
    selected_map = request.args.get('map', '')
    selected_stage = request.args.get('stage', '')

    # Get user's first name
    cursor.execute("SELECT first_name FROM users WHERE id = %s", (user_id,))
    user_row = cursor.fetchone()
    first_name = user_row['first_name'] if user_row and 'first_name' in user_row else "PLAYER"

    # Render the game template with the necessary context
    return render_template(
        'game.html',
        first_name=first_name,
        selected_map=selected_map,
        selected_stage=selected_stage
    )

@app.route('/save_progress', methods=['POST'])
def save_progress():
    if not session.get('user_id'):
        return jsonify({"error": "Not logged in"}), 403  # Unauthorized if not logged in

    user_id = session['user_id']
    data = request.get_json()

    map_name = data.get('map')
    stage_number = data.get('stage')
    stars = data.get('stars')

    if not map_name or not stage_number or stars is None:
        return jsonify({"error": "Missing data"}), 400

    cursor.execute("""
        SELECT * FROM user_progress 
        WHERE user_id = %s AND map_name = %s AND stage_number = %s
    """, (user_id, map_name, stage_number))
    existing_record = cursor.fetchone()

    if existing_record:
        cursor.execute("""
            UPDATE user_progress 
            SET stars = %s 
            WHERE user_id = %s AND map_name = %s AND stage_number = %s
        """, (stars, user_id, map_name, stage_number))
    else:
        cursor.execute("""
            INSERT INTO user_progress (user_id, map_name, stage_number, stars) 
            VALUES (%s, %s, %s, %s)
        """, (user_id, map_name, stage_number, stars))

    db.commit()

    return jsonify({"message": "Progress saved successfully"}), 200




@app.route('/get_stage_progress')
def get_stage_progress():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({})  # Return an empty response if the user is not logged in

    # Query to get all stage progress for the logged-in user
    cursor.execute("""
        SELECT map_name, stage_number, stars 
        FROM user_progress 
        WHERE user_id = %s
    """, (user_id,))

    rows = cursor.fetchall()

    # Prepare the stage progress in the required format
    progress = {}
    for row in rows:
        # Use a combined key for map and stage like 'subtraction-2'
        key = f"{row['map_name']}-{row['stage_number']}"
        progress[key] = {"stars": row['stars']}
    
    # Debug log to check the data structure
    print(progress)

    # Return the stage progress as JSON
    return jsonify(progress)




reward_data = {
    'multiplication': {
        1: {
            'badge': "/static/images/gameimg/rewardimg/badge/badge-1.png",
        },
        2: {
            'title': "/static/images/gameimg/rewardimg/title/title-1.png",
        },
        3: {
            'border': "/static/images/gameimg/rewardimg/border/border-1.png"
        }
    },
    'addition': {
        1: {
            'badge': "/static/images/gameimg/rewardimg/badge/badge-2.png",
        },
        2: {
            'title': "/static/images/gameimg/rewardimg/title/title-2.png",
        },
        3: {
            'border': "/static/images/gameimg/rewardimg/border/border-2.png"
        }
    },
    'subtraction': {
        1: {
            'badge': "/static/images/gameimg/rewardimg/badge/badge-3.png",
        },
        2: {
            'title': "/static/images/gameimg/rewardimg/title/title-3.png",
        },
        3: {
            'border': "/static/images/gameimg/rewardimg/border/border-3.png"
        }
    },
    'division': {
        1: {
            'badge': "/static/images/gameimg/rewardimg/badge/badge-4.png",
        },
        2: {
            'title': "/static/images/gameimg/rewardimg/title/title-4.png",
        },
        3: {
            'border': "/static/images/gameimg/rewardimg/border/border-4.png"
        }
    },
    'counting': {
        1: {
            'badge': "/static/images/gameimg/rewardimg/badge/badge-5.png",
        },
        2: {
            'title': "/static/images/gameimg/rewardimg/title/title-5.png",
        },
        3: {
            'border': "/static/images/gameimg/rewardimg/border/border-5.png"
        }
    },
    'comparison': {
        1: {
            'badge': "/static/images/gameimg/rewardimg/badge/badge-6.png",
        },
        2: {
            'title': "/static/images/gameimg/rewardimg/title/title-6.png",
        },
        3: {
            'border': "/static/images/gameimg/rewardimg/border/border-6.png"
        }
    },
    'numerals': {
        1: {
            'badge': "/static/images/gameimg/rewardimg/badge/badge-7.png",
        },
        2: {
            'title': "/static/images/gameimg/rewardimg/title/title-7.png",
        },
        3: {
            'border': "/static/images/gameimg/rewardimg/border/border-7.png"
        }
    },
    'placevalue': {
        1: {
            'badge': "/static/images/gameimg/rewardimg/badge/badge-8.png",
        },
        2: {
            'title': "/static/images/gameimg/rewardimg/title/title-8.png",
        },
        3: {
            'border': "/static/images/gameimg/rewardimg/border/border-8.png"
        }
    }
    # Add more maps and stages as needed
}

@app.route('/get_stage_reward', methods=['GET'])
def get_stage_reward():
    map_name = request.args.get('map')
    stage = request.args.get('stage')

    if not map_name or not stage:
        return jsonify({'error': 'Map and stage are required'}), 400

    try:
        stage = int(stage)
    except ValueError:
        return jsonify({'error': 'Stage must be an integer'}), 400

    if map_name not in reward_data:
        return jsonify({'error': 'Map not found'}), 404

    if stage not in reward_data[map_name]:
        return jsonify({'error': 'Stage not found for this map'}), 404

    return jsonify(reward_data[map_name][stage])



@app.route('/claim_reward', methods=['POST'])
def claim_reward():
    try:
        # Kunin ang user_id mula sa session
        user_id = session.get('user_id')
        
        # Kunin ang map_name at stage_number mula sa JSON body ng request
        map_name = request.json.get('map')
        stage_number = request.json.get('stage')

        # Siguraduhing kumpleto ang mga parameters
        if not user_id or not map_name or not stage_number:
            return jsonify({"error": "User ID, map, and stage parameters are required"}), 400
        
        print(f"Claiming reward for user_id={user_id}, map={map_name}, stage={stage_number}")

        # I-execute ang INSERT o UPDATE query sa database para i-claim ang reward
        cursor.execute("""
            INSERT INTO stage_rewards_claimed (user_id, map_name, stage_number, claimed)
            VALUES (%s, %s, %s, TRUE)
            ON DUPLICATE KEY UPDATE claimed = TRUE
        """, (user_id, map_name, stage_number))

        # I-commit ang changes sa database
        db.commit()

        print("Reward claimed successfully")
        
        # Ibalik ang success response
        return jsonify({"success": True})

    except Exception as e:
        # I-print ang error kung may mangyari
        print(f"[ERROR] /claim_reward failed: {e}")
        
        # Ibalik ang error response sa client
        return jsonify({"error": "Unable to claim reward"}), 500

@app.route('/check_reward_claimed', methods=['POST'])
def check_reward_claimed():
    try:
        # Retrieve the user ID from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not logged in"}), 400

        # Retrieve map and stage from the request
        map_name = request.json.get('map')
        stage_number = request.json.get('stage')

        if not map_name or not stage_number:
            return jsonify({"error": "Map and stage are required"}), 400

        # SQL query to check if the reward has been claimed
        cursor.execute("""
            SELECT claimed
            FROM stage_rewards_claimed
            WHERE user_id = %s AND map_name = %s AND stage_number = %s
        """, (user_id, map_name, stage_number))

        reward_claimed = cursor.fetchone()
        
        # Log the result of the query
        print(f"Reward claimed for user {user_id} on {map_name} stage {stage_number}: {reward_claimed}")

        if reward_claimed is None:
            return jsonify({"claimed": False})

        # Access the value correctly from the query result
        claimed = reward_claimed['claimed'] if reward_claimed else 0

        return jsonify({"claimed": bool(claimed)})

    except Exception as e:
        print(f"Error in /check_reward_claimed: {e}")
        return jsonify({"error": "Internal server error"}), 500







@app.route('/has_claimed_skin')
def has_claimed_skin():
    user_id = session.get('user_id')
    map_param = request.args.get('map')

    if not user_id or not map_param:
        print("Error: Missing user ID or map parameter")
        return jsonify({'claimed': False, 'error': 'Missing user ID or map parameter'})

    try:
        cursor = db.cursor()  # 🔧 Fresh cursor
        cursor.execute("""
            SELECT claimed FROM user_skins WHERE user_id = %s AND map = %s
        """, (user_id, map_param))
        result = cursor.fetchone()

        if result is None:
            print(f"Error: No result found for user {user_id} and map {map_param}")
            return jsonify({'claimed': False, 'error': 'No skin data found'})

        if result[0] == 1:
            return jsonify({'claimed': True})
        else:
            return jsonify({'claimed': False})

    except Exception as e:
        print(f"Error in /has_claimed_skin: {e}")
        return jsonify({'claimed': False, 'error': str(e)})
    finally:
        cursor.close()



@app.route('/claim_skin', methods=['POST'])
def claim_skin():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not logged in'})

    data = request.get_json()
    selected_map = data.get('map')

    if not selected_map:
        return jsonify({'error': 'Missing map parameter'}), 400

    skin_code_mapping = {
        'multiplication': 'r1',
        'addition': 'r2',
        'subtraction': 'r3',
        'division': 'r4',
        'counting': 'r5',
        'comparison': 'r6',
        'numerals': 'r7',
        'placevalue': 'r8',
    }

    skin_code = skin_code_mapping.get(selected_map)

    if not skin_code:
        return jsonify({'error': 'Invalid map provided'}), 400

    try:
        print(f"User {user_id} claiming skin for map: {selected_map} => skin_code: {skin_code}")

        cursor = db.cursor()  # 🔧 Create a new cursor here

        cursor.execute("""
            SELECT claimed FROM user_skins WHERE user_id = %s AND map = %s
        """, (user_id, selected_map))
        existing_skin = cursor.fetchone()

        if existing_skin and existing_skin[0] == 1:
            return jsonify({'success': False, 'message': 'Skin already claimed by this user'})

        if existing_skin:
            cursor.execute("""
                UPDATE user_skins SET claimed = 1, skin_code = %s
                WHERE user_id = %s AND map = %s
            """, (skin_code, user_id, selected_map))
        else:
            cursor.execute("""
                INSERT INTO user_skins (user_id, map, claimed, skin_code)
                VALUES (%s, %s, 1, %s)
            """, (user_id, selected_map, skin_code))

        db.commit()
        return jsonify({'success': True, 'message': 'Skin claimed successfully'})

    except Exception as e:
        print(f"Error in /claim_skin: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cursor.close()  # Close this route's cursor only

@app.route('/get_user_skins')
def get_user_skins():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not logged in'}), 401

    try:
        cursor = db.cursor()

        # Fetch claimed skins
        cursor.execute("""
            SELECT map, skin_code FROM user_skins WHERE user_id = %s AND claimed = 1
        """, (user_id,))
        skins = cursor.fetchall()

        # Get the equipped skin
        cursor.execute("""
            SELECT skin_code FROM user_skins WHERE user_id = %s AND equipped = 1 LIMIT 1
        """, (user_id,))
        equipped = cursor.fetchone()
        equipped_skin = equipped[0] if equipped else 'default'

        # Return skins data with equipped skin info
        return jsonify({
            'skins': [{'skin_code': skin[1], 'map': skin[0]} for skin in skins],
            'equipped_skin': equipped_skin
        })

    except Exception as e:
        print(f"Error fetching user skins: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cursor.close()





@app.route('/update_equipped_skin', methods=['POST'])
def update_equipped_skin():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not logged in'}), 401
    
    skin_id = request.json.get('skin_id')
    if skin_id is None:
        return jsonify({'error': 'Skin ID is required'}), 400

    try:
        cursor = db.cursor()

        # Allow 'default' skin
        if skin_id != 'default':
            cursor.execute("""
                SELECT * FROM user_skins WHERE user_id = %s AND skin_code = %s
            """, (user_id, skin_id))
            skin = cursor.fetchone()

            if not skin:
                return jsonify({'error': 'Skin not found for this user'}), 404

        # Unequip all skins first
        cursor.execute("""
            UPDATE user_skins SET equipped = 0 WHERE user_id = %s
        """, (user_id,))

        # Equip selected skin
        cursor.execute("""
            UPDATE user_skins SET equipped = 1 WHERE user_id = %s AND skin_code = %s
        """, (user_id, skin_id))

        # If no row was updated, insert the default skin
        if cursor.rowcount == 0 and skin_id == 'default':
            cursor.execute("""
                INSERT INTO user_skins (user_id, skin_code, map, claimed, equipped)
                VALUES (%s, 'default', NULL, 1, 1)
            """, (user_id,))

        db.commit()
        return jsonify({'message': 'Skin equipped successfully'})

    except Exception as e:
        print(f"Error equipping skin: {e}")
        db.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cursor.close()




def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),  # optional default
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

@app.route('/get-progress')
def get_progress():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not logged in'}), 400

    db = get_db_connection()
    if db is None:
        return jsonify({'success': False, 'message': 'Failed to connect to database'}), 500

    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM user_game_progress WHERE user_id = %s", (user_id,))
        rows = cursor.fetchall()

        if not rows:
            cursor.execute("""
                INSERT INTO user_game_progress (user_id, map, stage_key, correct, wrong, total, difficulty)
                VALUES (%s, 'multiplication', 'stage1', 0, 0, 0, 'easy')
            """, (user_id,))
            db.commit()

            cursor.execute("SELECT * FROM user_game_progress WHERE user_id = %s", (user_id,))
            rows = cursor.fetchall()

        result = {'success': True, 'mapDifficulty': {}, 'selectedMap': 'multiplication', 'selectedStageKey': 'stage1'}

        for row in rows:
            map_name = row['map']
            result['mapDifficulty'][map_name] = row['difficulty']
            result[map_name] = {
                'correctAnswersCount': row['correct'],
                'wrongAnswersCount': row['wrong'],
                'totalQuestionsAnswered': row['total']
            }

        return jsonify(result)
    
    except Exception as e:
        print(f"Error loading progress: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.close()

@app.route('/save-game-progress', methods=['POST'])
def save_game_progress():
    try:
        data = request.get_json()
        user_id = session.get('user_id')

        if not user_id:
            raise ValueError("User not logged in")

        selected_map = data.get('map')
        selected_stage = data.get('stage')
        correct = data.get('correctAnswersCount', 0)
        wrong = data.get('wrongAnswersCount', 0)
        total = data.get('totalQuestionsAnswered', 0)
        difficulty = data.get('difficulty')

        db = get_db_connection()
        if db is None:
            raise ConnectionError("Failed to connect to the database")
        
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO user_game_progress (user_id, map, stage_key, correct, wrong, total, difficulty)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            correct = VALUES(correct),
            wrong = VALUES(wrong),
            total = VALUES(total),
            difficulty = VALUES(difficulty)
        """, (user_id, selected_map, selected_stage, correct, wrong, total, difficulty))
        
        db.commit()
        
        return jsonify({'success': True, 'message': 'Progress saved successfully'})

    except ValueError as ve:
        print(f"ValueError: {ve}")
        return jsonify({'success': False, 'message': str(ve)}), 400  # Bad request
    except ConnectionError as ce:
        print(f"ConnectionError: {ce}")
        return jsonify({'success': False, 'message': str(ce)}), 500  # Internal server error
    except mysql.connector.Error as mysql_err:
        print(f"MySQL Error: {mysql_err}")
        return jsonify({'success': False, 'message': 'Database error occurred'}), 500  # Internal server error
    except Exception as e:
        print(f"Exception: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred'}), 500  # Generic server error
    finally:
        if db:
            db.close()


@app.route('/get-difficulty')
def get_difficulty():
    user_id = session.get('user_id')
    map_name = request.args.get('map')

    db = get_db_connection()
    if db is None:
        return jsonify({'success': False, 'message': 'Failed to connect to database'}), 500

    cursor = db.cursor()
    cursor.execute("SELECT difficulty FROM user_game_progress WHERE user_id = %s AND map = %s", (user_id, map_name))
    result = cursor.fetchone()

    if result:
        return jsonify({'success': True, 'difficulty': result[0]})
    return jsonify({'success': False})

@app.route('/update-difficulty', methods=['POST'])
def update_difficulty():
    data = request.json
    user_id = session.get('user_id')
    map_name = data['map']
    difficulty = data['difficulty']

    db = get_db_connection()
    if db is None:
        return jsonify({'success': False, 'message': 'Failed to connect to database'}), 500

    cursor = db.cursor()
    cursor.execute("""
        UPDATE user_game_progress SET difficulty = %s WHERE user_id = %s AND map = %s
    """, (difficulty, user_id, map_name))

    db.commit()
    return jsonify({'success': True})


@app.route('/reset-counters', methods=['POST'])
def reset_counters():
    data = request.get_json()
    user_id = session.get('user_id')  # Make sure user is logged in
    selected_map = data.get('map')

    if not user_id or not selected_map:
        return jsonify({"message": "Missing user ID or map"}), 400

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        reset_query = """
            UPDATE user_game_progress
            SET correct = 0,
                wrong = 0,
                total = 0
            WHERE user_id = %s AND map = %s
        """

        print(f"Executing query: {reset_query} with params: (user_id={user_id}, map={selected_map})")

        cursor.execute(reset_query, (user_id, selected_map))
        connection.commit()

        if cursor.rowcount > 0:
            return jsonify({"message": "Counters reset successfully!"}), 200
        else:
            return jsonify({"message": "No progress found for this map."}), 404

    except Exception as e:
        connection.rollback()
        print("❌ Error resetting counters:", str(e))
        return jsonify({"message": "Error resetting counters", "error": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    app.run(debug=True)

    