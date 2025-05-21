from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_bcrypt import Bcrypt
from flask import request, jsonify
import mysql.connector
import openai

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this later

# Initialize extensions
bcrypt = Bcrypt(app)

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="qweqwe",
    database="learning_game"
)
cursor = db.cursor(dictionary=True)

# 🔥 OpenRouter Setup
openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key = "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"  # ← Replace this with your OpenRouter API Key

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





# ✅ CHATBOT API ROUTE
user_question_status = {}
user_last_question = {}

@app.route('/chatbot-api', methods=['POST'])
def chatbot_api():
    try:
        user_message = request.json['message'].strip().lower()

        # For simplicity, assuming one global user — if you're using logins, use session/user_id keys
        global_user_id = "default_user"

        # Initialize user state if not yet present
        if global_user_id not in user_last_question:
            user_last_question[global_user_id] = None

        follow_ups = [
            "i don't know", "can you help", "i still don't get it", 
            "i need help", "what now", "i’m confused", "i dont know"
        ]

        # Check if it's a follow-up
        if user_message in follow_ups and user_last_question[global_user_id]:
            # It's a follow-up to a previous question
            original_question = user_last_question[global_user_id]
            user_message = original_question
            asked_before = True
        else:
            # New question
            original_question = user_message
            asked_before = user_question_status.get(user_message, False)
            user_last_question[global_user_id] = user_message  # Remember this as the last question

        # Set the prompt based on whether it’s the first or second time asking
        if asked_before:
            prompt = (
                "You are Counticus, a kind and friendly math wizard who loves helping little kids learn math. "
                "Pretend you are talking to a Grade 1 student, so use very simple words and speak slowly and gently. "
                "When a child asks the same math question again, it means they want more help. So now, explain the steps one by one, like you’re guiding them. "
                "Use easy words and make each step clear. Then, give the final answer at the end. "
                "Be very patient and speak like a caring teacher. Example: 'First, we take 3 apples... then we add 2 more... so now we have...?'"
            )
        else:
            prompt = (
                "You are Counticus, a kind and friendly math wizard who loves helping little kids learn math. "
                "Pretend you are talking to a Grade 1 student, so use very simple words and speak slowly and gently. "
                "When a child asks a math question for the first time, don’t give the final answer. Instead, give helpful hints, like clues, or tell them how they can start solving it. "
                "Be patient and cheerful, like a teacher who’s very good with kids. Example: 'Hmm, let’s try counting together!' or 'Can you think of what comes after 5?'"
            )

        # Make the OpenAI API call
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ]
        )

        # Get the reply
        reply = response['choices'][0]['message']['content'].strip()

        # Mark that this question has now been asked
        user_question_status[original_question] = True

        return jsonify({"reply": reply})

    except Exception as e:
        print("❌ Chatbot Error:", e)
        return jsonify({"reply": "Oops! Counticus couldn’t reach the magic scrolls. Try again later."})


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

@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

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
            host="localhost",
            user="root",
            password="qweqwe",  # Replace this with your actual password
            database="learning_game"
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

    