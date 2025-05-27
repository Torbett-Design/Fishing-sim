import random
import time
import json
import os
import sys

class InteractionEngine:
    def __init__(self, game_instance):
        self.game = game_instance
        self.interactions_data = self.load_interactions()
        
        # Define custom trigger functions
        self.custom_triggers = {
            "add_fish_catch": self.add_fish_catch,
            "add_unusual_catch": self.add_unusual_catch
        }
        
    def load_interactions(self):
        """Load interaction definitions from JSON"""
        try:
            with open('interactions.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Warning: interactions.json not found. Using minimal interactions.")
            return {"objects": {}, "verbs": {}, "message_pools": {}, "triggers": {}}
    
    def resolve_object_alias(self, obj_name):
        """Resolve object aliases to canonical names"""
        for obj_id, obj_data in self.interactions_data.get("objects", {}).items():
            if obj_name == obj_id or obj_name in obj_data.get("aliases", []):
                return obj_id
        return obj_name
    
    def check_conditions(self, conditions):
        """Check if conditions are met for an interaction"""
        for condition, required_value in conditions.items():
            if "." in condition:
                # Object property check (e.g., "rod.assembled")
                obj_name, prop = condition.split(".", 1)
                obj_data = self.interactions_data.get("objects", {}).get(obj_name, {})
                current_value = obj_data.get("properties", {}).get(prop, False)
            else:
                # Game state check
                current_value = getattr(self.game, condition, False)
            
            if current_value != required_value:
                return False
        return True
    
    def check_requirements(self, requirements):
        """Check if requirements are met"""
        for req in requirements:
            if "." in req:
                obj_name, prop = req.split(".", 1)
                obj_data = self.interactions_data.get("objects", {}).get(obj_name, {})
                if not obj_data.get("properties", {}).get(prop, False):
                    return False
            else:
                if not getattr(self.game, req, False):
                    return False
        return True
    
    def apply_effects(self, effects):
        """Apply stat changes"""
        for stat, change in effects.items():
            if hasattr(self.game, stat):
                current = getattr(self.game, stat)
                if isinstance(current, (int, float)):
                    new_value = max(0, min(100, current + change))
                    setattr(self.game, stat, new_value)
    
    def apply_property_changes(self, obj_name, changes):
        """Apply changes to object properties"""
        if obj_name in self.interactions_data.get("objects", {}):
            obj_props = self.interactions_data["objects"][obj_name].setdefault("properties", {})
            obj_props.update(changes)
    
    def apply_game_state_changes(self, changes):
        """Apply changes to game state"""
        for attr, value in changes.items():
            setattr(self.game, attr, value)
    
    def execute_triggers(self, triggers):
        """Execute special triggers including custom functions"""
        for trigger_name in triggers:
            if trigger_name in self.custom_triggers:
                self.custom_triggers[trigger_name]()
            else:
                trigger_data = self.interactions_data.get("triggers", {}).get(trigger_name, {})
                if "effects" in trigger_data:
                    self.apply_effects(trigger_data["effects"])
                
                # Special trigger handling
                if trigger_name == "escalate_chaos":
                    self.game.escalate_chaos()
    
    def get_message_from_pool(self, pool_name):
        """Get random message from a message pool"""
        pool = self.interactions_data.get("message_pools", {}).get(pool_name, [])
        return random.choice(pool) if pool else "Something interesting happens."
    
    def add_fish_catch(self):
        """Add a fish to the catch list"""
        fish_types = self.game.get_text("fish_types", [])
        if not fish_types:
            fish_types = ["Brown Trout", "Rainbow Trout", "Grayling", "Pike", "Perch", "Roach"]
        
        fish_name = random.choice(fish_types)
        description = f"A fine {fish_name.lower()} caught with scholarly precision"
        self.game.add_to_catch(fish_name, description)

    def add_unusual_catch(self):
        """Add an unusual item to the catch list"""
        unusual_messages = self.interactions_data.get("message_pools", {}).get("unusual_catches", [])
        if not unusual_messages:
            unusual_messages = [
                "You reel in... a boot. It's not even a matching pair with the one you caught yesterday.",
                "Success! You've caught a magnificent... stick. The stick appears unimpressed by your angling prowess.",
                "You reel in what might be the world's most philosophical piece of pond weed."
            ]
        
        message = random.choice(unusual_messages)
        
        # Extract item name and add to catch
        if "boot" in message.lower():
            item_name = "Old Boot"
            description = "A waterlogged boot of mysterious origin"
        elif "stick" in message.lower():
            item_name = "Philosophical Stick"
            description = "A piece of driftwood with apparent opinions"
        elif "pond weed" in message.lower():
            item_name = "Pond Weed"
            description = "Aquatic vegetation with existential concerns"
        elif "rubber duck" in message.lower():
            item_name = "Rubber Duck"
            description = "A squeaky witness to Harvey's angling attempts"
        elif "tin can" in message.lower():
            item_name = "Tin Can"
            description = "Contains what appears to be complaints about river management"
        elif "traffic cone" in message.lower():
            item_name = "Traffic Cone"
            description = "A small orange mystery of aquatic engineering"
        elif "teddy bear" in message.lower():
            item_name = "Teddy Bear"
            description = "A waterlogged witness to unspeakable aquatic horrors"
        else:
            item_name = "Mysterious Object"
            description = "Something that defies classification"
        
        # Add to the game's catch list
        self.game.add_to_catch(item_name, description)
        
        # Display the message
        if self.game.brandy_level > 0:
            message = self.game.apply_brandy_effects(message)
        print(f"\n🎭 {message}")

    def execute_interaction(self, verb, obj_name):
        """Enhanced interaction execution with brandy effects"""
        # Resolve aliases
        canonical_obj = self.resolve_object_alias(obj_name)
        
        # Get object and verb data
        obj_data = self.interactions_data.get("objects", {}).get(canonical_obj, {})
        verb_data = self.interactions_data.get("verbs", {}).get(verb, {})
        
        # Check if interaction exists
        interaction = obj_data.get("interactions", {}).get(verb)
        
        if not interaction:
            # Use generic response
            generic_msg = verb_data.get("generic_response", f"Harvey cannot {verb} {obj_name}.")
            message = generic_msg.format(object=obj_name, verb=verb)
            self.game.refresh_display(f"\n{message}")
            return
        
        # Check conditions and requirements
        conditions = interaction.get("conditions", {})
        requirements = interaction.get("requires", [])
        
        if not self.check_conditions(conditions):
            failure_msg = interaction.get("condition_failure_message", f"The conditions aren't right to {verb} {obj_name}.")
            self.game.refresh_display(f"\n{failure_msg}")
            return
        
        if not self.check_requirements(requirements):
            req_msg = interaction.get("requirement_failure_message", f"Harvey needs something else before he can {verb} {obj_name}.")
            self.game.refresh_display(f"\n{req_msg}")
            return
        
        # Determine outcome
        success_chance = interaction.get("success_chance", 1.0)
        outcomes = interaction.get("outcomes", {})
        
        if random.random() < success_chance and "success" in outcomes:
            outcome = outcomes["success"]
        elif "failure" in outcomes:
            outcome = outcomes["failure"]
        else:
            # Simple interaction without success/failure
            outcome = interaction
        
        # Get message
        if "message_pool" in outcome:
            message = self.get_message_from_pool(outcome["message_pool"])
        else:
            message = outcome.get("message", f"Harvey {verb}s {obj_name}.")
        
        # Apply effects
        if "effects" in outcome:
            self.apply_effects(outcome["effects"])
        
        if "property_changes" in outcome:
            self.apply_property_changes(canonical_obj, outcome["property_changes"])
        
        if "game_state_changes" in outcome:
            self.apply_game_state_changes(outcome["game_state_changes"])
        
        if "triggers" in outcome:
            self.execute_triggers(outcome["triggers"])
        
        # Apply brandy effects to the message if Harvey has been drinking
        if hasattr(self.game, 'brandy_level') and self.game.brandy_level > 0:
            message = self.game.apply_brandy_effects(message)
            
            # Add random brandy-influenced responses
            modifiers = self.game.get_brandy_modifier()
            if random.random() < 0.3:  # 30% chance of additional brandy response
                brandy_pool = f"brandy_responses_{modifiers['mood']}"
                if brandy_pool in self.interactions_data.get("message_pools", {}):
                    brandy_msg = self.get_message_from_pool(brandy_pool)
                    message += f"\n\n{self.game.apply_brandy_effects(brandy_msg)}"
        
        self.game.refresh_display(f"\n{message}")

class FishingGame:
    def __init__(self):
        # Clear terminal on startup
        self.clear_terminal()
        
        # Use cryptographically secure random seed
        random.seed(int(time.time()*100))
        
        self.player_name = "Harvey Torbett"
        
        # Load all data first
        self.responses = self.load_responses()
        self.locations_data = self.load_locations()
        
        # Randomly select location at game start
        self.location_data = self.select_random_location()
        self.location = self.location_data["name"]
        self.location_type = self.location_data["type"]
        
        self.attempts = 0
        self.determination = 100
        self.rod_attached = False
        self.fly_attached = False
        self.cast_made = False
        self.weather = "pleasant"
        self.sandwich_status = "dry"
        self.waders_status = "intact"
        self.hat_status = "on head"
        self.dignity = 75
        self.fish_caught = 0
        self.game_over = False
        
        # Harvey's scholarly state
        self.inspiration_level = 50
        self.academic_reputation = 85
        
        # Slower escalating mishap categories - increased max level
        self.mishap_level = 0
        self.max_mishap_level = 8  # Increased from 5
        
        # Track successful actions for positive momentum
        self.successful_actions = 0
        self.consecutive_failures = 0
        
        # New inventory and catch systems
        self.current_catch = []
        self.kit_bag = self.initialize_kit_bag()
        self.brandy_level = 0  # 0-6, affects Harvey's responses
        self.thermos_contents = self.determine_thermos_contents()
        self.thermos_remaining = 6  # Number of drinks left
        
        # Initialize interaction engine
        self.interaction_engine = InteractionEngine(self)
        
        # Define verbs (actions) and their valid objects
        self.verbs = {
            'attach': {
                'method': self.attach,
                'objects': ['fly', 'rod', 'line', 'reel'],
                'help': 'Attach something to your fishing equipment'
            },
            'cast': {
                'method': self.cast,
                'objects': ['rod', 'line'],
                'help': 'Cast your fishing line'
            },
            'reel': {
                'method': self.reel,
                'objects': ['in', 'line'],
                'help': 'Reel in your line'
            },
            'eat': {
                'method': self.eat,
                'objects': ['sandwich', 'lunch', 'food'],
                'help': 'Consume something edible'
            },
            'drink': {
                'method': self.drink,
                'objects': ['tea', 'water', 'thermos', 'brandy'],
                'help': 'Drink something refreshing'
            },
            'examine': {
                'method': self.examine,
                'objects': ['rod', 'fly', 'water', 'sandwich', 'hat', 'waders', 'gear', 'surroundings', 'thermos'],
                'help': 'Look closely at something'
            },
            'adjust': {
                'method': self.adjust,
                'objects': ['hat', 'glasses', 'waders', 'reel'],
                'help': 'Make adjustments to your equipment'
            },
            'wade': {
                'method': self.wade,
                'objects': ['deeper', 'out', 'upstream', 'downstream'],
                'help': 'Move through the water'
            },
            'change': {
                'method': self.change,
                'objects': ['fly', 'position', 'location'],
                'help': 'Change or swap something'
            },
            'tie': {
                'method': self.tie,
                'objects': ['knot', 'fly', 'line'],
                'help': 'Tie knots or secure equipment'
            },
            'clean': {
                'method': self.clean,
                'objects': ['glasses', 'rod', 'reel'],
                'help': 'Clean your equipment'
            },
            'check': {
                'method': self.check,
                'objects': ['gear', 'weather', 'time', 'water', 'surroundings'],
                'help': 'Check the status of something'
            },
            'take': {
                'method': self.take,
                'objects': ['notes', 'break', 'photo'],
                'help': 'Take or pick up something'
            },
            # Actions that don't need objects
            'sing': {
                'method': self.sing,
                'objects': [],
                'help': 'Sing a song'
            },
            'whistle': {
                'method': self.whistle,
                'objects': [],
                'help': 'Whistle a tune'
            },
            'dance': {
                'method': self.dance,
                'objects': [],
                'help': 'Dance with abandon'
            },
            'pray': {
                'method': self.pray,
                'objects': [],
                'help': 'Pray for better luck'
            },
            'curse': {
                'method': self.curse,
                'objects': [],
                'help': 'Express frustration colorfully'
            },
            'meditate': {
                'method': self.meditate,
                'objects': [],
                'help': 'Find inner peace'
            },
            'contemplate': {
                'method': self.contemplate,
                'objects': [],
                'help': 'Engage in deep thought'
            },
            'theorize': {
                'method': self.theorize,
                'objects': [],
                'help': 'Develop academic theories'
            },
            'lecture': {
                'method': self.give_lecture,
                'objects': [],
                'help': 'Deliver an impromptu academic lecture'
            },
            'quote': {
                'method': self.random_quote,
                'objects': [],
                'help': 'Share wisdom from your bibliography'
            },
            'look': {
                'method': self.look,
                'objects': ['around', 'water', 'sky', 'trees', 'gear'],
                'help': 'Look at your surroundings'
            },
            'go': {
                'method': self.go,
                'objects': ['home', 'upstream', 'downstream', 'deeper'],
                'help': 'Move to a different location'
            }
        }
        
        # Simple commands that don't need parsing
        self.simple_commands = {
            'help': self.show_help,
            'commands': self.show_help,
            'stats': self.show_stats,
            'inventory': self.check_gear,
            'bibliography': self.show_bibliography,
            'quit': self.give_up,
            'exit': self.give_up,
            'catch': self.show_catch,
            'kit': self.show_kit_bag,
            'bag': self.show_kit_bag
        }

    def initialize_kit_bag(self):
        """Initialize Harvey's kit bag with starting items"""
        return {
            "sandwich": {
                "name": "Cucumber Sandwich",
                "description": "A properly made cucumber sandwich with the crusts removed",
                "status": "dry",
                "consumable": True,
                "uses_remaining": 1
            },
            "thermos": {
                "name": "Thermos Flask",
                "description": "A well-worn thermos flask of indeterminate age",
                "consumable": True,
                "uses_remaining": 6,
                "contents": None  # Will be determined separately
            },
            "spectacles": {
                "name": "Reading Spectacles",
                "description": "Harvey's scholarly spectacles, essential for proper observation",
                "consumable": False
            },
            "notebook": {
                "name": "Leather-bound Notebook",
                "description": "For recording observations and developing theories",
                "consumable": False
            },
            "pocket_watch": {
                "name": "Grandfather's Pocket Watch",
                "description": "A reliable timepiece inherited from Harvey's grandfather",
                "consumable": False
            }
        }

    def determine_thermos_contents(self):
        """Randomly determine what's in the thermos - usually tea, sometimes brandy!"""
        contents_options = [
            {"type": "tea", "name": "Earl Grey Tea", "probability": 0.7},
            {"type": "tea", "name": "English Breakfast Tea", "probability": 0.15},
            {"type": "brandy", "name": "Fine Brandy", "probability": 0.15}
        ]
        
        rand = random.random()
        cumulative = 0
        for option in contents_options:
            cumulative += option["probability"]
            if rand <= cumulative:
                self.kit_bag["thermos"]["contents"] = option
                return option
        
        # Fallback to tea
        return {"type": "tea", "name": "Earl Grey Tea"}

    def add_to_catch(self, item_name, description=""):
        """Add an item to the current catch"""
        catch_item = {
            "name": item_name,
            "description": description,
            "caught_at": self.attempts,
            "location": self.location
        }
        self.current_catch.append(catch_item)

    def get_brandy_modifier(self):
        """Get text modifiers based on brandy consumption level"""
        if self.brandy_level == 0:
            return {"slur": False, "typos": False, "hiccups": False, "mood": "normal"}
        elif self.brandy_level <= 2:
            return {"slur": False, "typos": True, "hiccups": False, "mood": "merry"}
        elif self.brandy_level <= 4:
            return {"slur": True, "typos": True, "hiccups": True, "mood": "jolly"}
        else:
            return {"slur": True, "typos": True, "hiccups": True, "mood": "thoroughly_tipsy"}

    def apply_brandy_effects(self, text):
        """Apply brandy-induced modifications to text"""
        if self.brandy_level == 0:
            return text
        
        modifiers = self.get_brandy_modifier()
        modified_text = text
        
        # Apply typos
        if modifiers["typos"]:
            typo_replacements = {
                "the": "teh", "and": "adn", "fishing": "fishign", "water": "waetr",
                "excellent": "excelent", "magnificent": "magnifcent", "scholarly": "scholalry",
                "academic": "acadmeic", "precisely": "preciesly", "definitely": "definately"
            }
            for correct, typo in typo_replacements.items():
                if random.random() < 0.3:  # 30% chance of each typo
                    modified_text = modified_text.replace(correct, typo)
        
        # Apply slurring
        if modifiers["slur"]:
            slur_replacements = {
                "s": "sh", "fishing": "fishhing", "this": "thish", "success": "shuccess",
                "scholarly": "shcolarly", "splendid": "shplendid"
            }
            for normal, slurred in slur_replacements.items():
                if random.random() < 0.2:  # 20% chance
                    modified_text = modified_text.replace(normal, slurred)
        
        # Add hiccups
        if modifiers["hiccups"] and random.random() < 0.4:
            hiccup_positions = [len(modified_text) // 3, 2 * len(modified_text) // 3]
            for pos in hiccup_positions:
                if random.random() < 0.5:
                    modified_text = modified_text[:pos] + " *hic* " + modified_text[pos:]
        
        return modified_text

    def parse_command(self, command_text):
        """Parse command into verb and object"""
        words = command_text.lower().strip().split()
        
        if not words:
            return None, None
            
        verb = words[0]
        obj = ' '.join(words[1:]) if len(words) > 1 else None
        
        return verb, obj

    def execute_command(self, command_text):
        """Execute a parsed command using the interaction engine"""
        # Handle simple commands
        if command_text in self.simple_commands:
            self.simple_commands[command_text]()
            return
        
        verb, obj = self.parse_command(command_text)
        
        if not verb:
            self.refresh_display("\nHarvey adjusts his spectacles, waiting for instruction.")
            return
        
        # For certain verbs, always use the old system first
        priority_verbs = ['drink', 'attach', 'cast']  # Add verbs that should use old system
        
        if verb in priority_verbs and verb in self.verbs:
            # Use old verb system for priority verbs
            verb_data = self.verbs[verb]
            
            # Check if verb requires an object
            if verb_data['objects'] and not obj:
                objects_list = ', '.join(verb_data['objects'])
                self.refresh_display(f"\nWhat do you want to {verb}? Try: {objects_list}")
                return
            
            # Execute the command
            try:
                if obj:
                    verb_data['method'](obj)
                else:
                    verb_data['method']()
            except Exception as e:
                self.refresh_display(f"\nSomething went awry while trying to {verb} {obj or ''}.")
            return
        
        # Try interaction engine for other verbs
        if obj and verb in self.interaction_engine.interactions_data.get("verbs", {}):
            self.interaction_engine.execute_interaction(verb, obj)
            return
        
        # Fall back to old verb system
        if verb not in self.verbs:
            self.refresh_display(f"\nHarvey ponders '{verb}' but finds it beyond his current vocabulary.")
            return
        
        verb_data = self.verbs[verb]
        
        # Check if verb requires an object
        if verb_data['objects'] and not obj:
            objects_list = ', '.join(verb_data['objects'])
            self.refresh_display(f"\nWhat do you want to {verb}? Try: {objects_list}")
            return
        
        # Execute the command
        try:
            if obj:
                verb_data['method'](obj)
            else:
                verb_data['method']()
        except Exception as e:
            self.refresh_display(f"\nSomething went awry while trying to {verb} {obj or ''}.")


    # Updated action methods that handle objects
    def attach(self, obj):
        """Handle attach commands - now uses interaction engine"""
        if obj in ['fly']:
            # Use old system for fly (it's complex with game state)
            self.attach_fly()
        elif obj in ['rod']:
            # Use old system for rod (it's complex with game state)
            self.attach_rod()
        elif obj in self.interaction_engine.interactions_data.get("objects", {}):
            # Use interaction engine for other objects
            self.interaction_engine.execute_interaction('attach', obj)
        elif obj in ['line', 'reel']:
            message = f"Harvey examines his {obj} and determines it's already properly attached, though he appreciates your attention to detail."
            self.refresh_display(f"\n{message}")
        else:
            message = f"Harvey cannot attach '{obj}' - it's either already attached or not part of his fishing kit."
            self.refresh_display(f"\n{message}")

    def cast(self, obj=None):
        """Handle cast commands - now uses interaction engine"""
        if obj in ['rod', 'line'] or obj is None:
            # Use old system for rod casting (it's complex)
            self.cast_rod()
        elif obj in self.interaction_engine.interactions_data.get("objects", {}):
            # Use interaction engine for casting other objects
            self.interaction_engine.execute_interaction('cast', obj)
        else:
            message = f"Harvey cannot cast '{obj}'. Perhaps you meant 'cast rod'?"
            self.refresh_display(f"\n{message}")

    def reel(self, obj):
        """Handle reel commands"""
        if obj in ['in', 'line']:
            self.reel_in()
        else:
            message = f"Harvey is unsure how to reel '{obj}'. Try 'reel in'."
            self.refresh_display(f"\n{message}")

    def eat(self, obj):
        """Handle eat commands - now uses interaction engine"""
        if obj in ['sandwich', 'lunch', 'food']:
            # Use interaction engine for sandwich
            self.interaction_engine.execute_interaction('eat', 'sandwich')
        elif obj in self.interaction_engine.interactions_data.get("objects", {}):
            # Use interaction engine for other objects
            self.interaction_engine.execute_interaction('eat', obj)
        else:
            message = f"Harvey examines '{obj}' and determines it's not suitable for consumption, even by British standards."
            self.refresh_display(f"\n{message}")

    def drink(self, obj):
        """Handle drink commands - bypass interaction engine for now"""
        
        if obj in ['thermos', 'tea', 'brandy']:
            # Use the existing thermos drinking logic
            self.drink_thermos()
        elif obj == 'water':
            # Handle water drinking directly
            message = "Harvey cups some river water in his hands and takes a tentative sip. 'Hmm. Notes of limestone, hints of watercress, with a lingering finish of... is that duck?'"
            self.refresh_display(f"\n{message}")
            self.determination = min(100, self.determination + 3)
            self.dignity = max(0, self.dignity - 5)
            self.inspiration_level = min(100, self.inspiration_level + 5)
        else:
            message = f"Harvey cannot drink '{obj}' - perhaps you meant 'drink thermos'?"
            self.refresh_display(f"\n{message}")


    def examine(self, obj):
        """Handle examine commands - now uses interaction engine"""
        # Special handling for thermos to show contents
        if obj == 'thermos':
            contents = self.thermos_contents
            remaining = self.thermos_remaining
            if remaining > 0:
                message = f"The thermos contains {contents['name']}. {remaining} servings remain. Harvey contemplates the delights within."
            else:
                message = "The thermos is empty, leaving Harvey to contemplate the philosophical implications of an empty vessel."
            
            self.refresh_display(f"\n{message}")
            self.inspiration_level = min(100, self.inspiration_level + 2)
            return
        
        # Try interaction engine for other objects
        if obj in self.interaction_engine.interactions_data.get("objects", {}):
            self.interaction_engine.execute_interaction('examine', obj)
        else:
            # Fall back to old system for objects not in interactions.json
            examinations = self.get_text("examinations", {})
            
            fallback_examinations = {
                'rod': "Harvey's rod gleams in the light, a testament to fine British craftsmanship.",
                'fly': "The fly is a work of art - delicate feathers and precise construction designed to fool the most discerning trout.",
                'water': "The water flows with the kind of purposeful determination Harvey wishes he possessed.",
                'sandwich': f"The sandwich appears to be in {self.sandwich_status} condition, a portable monument to British culinary pragmatism.",
                'hat': f"Harvey's hat sits {self.hat_status}, maintaining the dignity expected of a gentleman scholar.",
                'waders': f"The waders are currently {self.waders_status}, serving as a reminder of the ongoing battle between man and nature.",
                'gear': "Harvey's fishing gear represents decades of angling evolution, though the fish seem unimpressed by this heritage.",
                'surroundings': "The natural beauty surrounding Harvey provides the perfect backdrop for his ongoing dialogue with aquatic disappointment."
            }
            
            description = examinations.get(obj, fallback_examinations.get(obj, f"Harvey examines '{obj}' with scholarly interest, making mental notes for future reference."))
            self.refresh_display(f"\n{description}")
            
    def adjust(self, obj):
        """Handle adjust commands"""
        if obj == 'hat':
            self.adjust_hat()
        elif obj == 'glasses':
            self.clean_glasses()
        elif obj in ['waders', 'reel']:
            message = f"Harvey carefully adjusts his {obj}, achieving a marginal improvement in comfort if not in fishing success."
            self.refresh_display(f"\n{message}")
            self.determination += random.randint(1, 3)
        else:
            message = f"Harvey cannot adjust '{obj}' - it's either not adjustable or not present."
            self.refresh_display(f"\n{message}")

    def wade(self, obj):
        """Handle wade commands"""
        if obj == 'deeper':
            self.wade_deeper()
        elif obj == 'out':
            message = "Harvey wades back toward shore, reassessing his aquatic strategy."
            self.refresh_display(f"\n{message}")
            self.determination += 3
        else:
            message = f"Harvey considers wading {obj}, but decides against it for reasons of safety and dignity."
            self.refresh_display(f"\n{message}")

    def change(self, obj):
        """Handle change commands"""
        if obj == 'fly':
            self.change_fly()
        elif obj in ['position', 'location']:
            message = f"Harvey considers changing his {obj}, but decides that disappointment is portable and will likely follow him anywhere."
            self.refresh_display(f"\n{message}")
            self.determination += random.randint(1, 5)
        else:
            message = f"Harvey cannot change '{obj}' - some things are beyond even scholarly intervention."
            self.refresh_display(f"\n{message}")

    def tie(self, obj):
        """Handle tie commands"""
        if obj in ['knot', 'fly', 'line']:
            self.tie_knot()
        else:
            message = f"Harvey cannot tie '{obj}' - his expertise is limited to fishing knots and academic arguments."
            self.refresh_display(f"\n{message}")

    def clean(self, obj):
        """Handle clean commands"""
        if obj == 'glasses':
            self.clean_glasses()
        elif obj in ['rod', 'reel']:
            message = f"Harvey meticulously cleans his {obj}, achieving a level of spotlessness that would make his mother proud."
            self.refresh_display(f"\n{message}")
            self.determination += random.randint(2, 5)
            self.dignity += random.randint(1, 3)
        else:
            message = f"Harvey cannot clean '{obj}' - some things are beyond redemption."
            self.refresh_display(f"\n{message}")

    def check(self, obj):
        """Handle check commands"""
        if obj == 'gear':
            self.check_gear()
        elif obj == 'weather':
            self.check_weather()
        elif obj == 'time':
            self.check_time()
        elif obj in ['water', 'surroundings']:
            self.look_around()
        else:
            message = f"Harvey checks his {obj} with scholarly thoroughness, finding it to be exactly as expected."
            self.refresh_display(f"\n{message}")

    def take(self, obj):
        """Handle take commands"""
        if obj == 'notes':
            self.take_notes()
        elif obj == 'break':
            message = "Harvey takes a moment to appreciate the natural beauty around him, finding renewed inspiration in the peaceful surroundings."
            self.refresh_display(f"\n{message}")
            self.determination += random.randint(5, 10)
            self.inspiration_level = min(100, self.inspiration_level + 5)
        elif obj == 'photo':
            message = "Harvey carefully composes a mental photograph of the scene, filing it away for future reference in his scholarly works."
            self.refresh_display(f"\n{message}")
            self.inspiration_level = min(100, self.inspiration_level + 3)
        else:
            message = f"Harvey cannot take '{obj}' - his hands are full with fishing equipment and academic pursuits."
            self.refresh_display(f"\n{message}")

    def look(self, obj=None):
        """Handle look commands"""
        if obj in ['around', 'surroundings'] or obj is None:
            self.look_around()
        elif obj == 'water':
            self.examine('water')
        elif obj == 'sky':
            self.check_weather()
        else:
            self.examine(obj)

    def go(self, obj):
        """Handle movement commands"""
        if obj == 'home':
            self.give_up()
        elif obj in ['deeper']:
            self.wade_deeper()
        elif obj in ['upstream', 'downstream']:
            message = f"Harvey considers moving {obj}, but decides his current position offers optimal opportunities for continued failure."
            self.refresh_display(f"\n{message}")
        else:
            message = f"Harvey cannot go '{obj}' from here."
            self.refresh_display(f"\n{message}")

    def show_catch(self):
        """Display current catch"""
        if not self.current_catch:
            message = "Harvey's catch bag is disappointingly empty, though rich in potential for future anecdotes."
        else:
            message = f"\n--- HARVEY'S CATCH ---\n"
            for i, item in enumerate(self.current_catch, 1):
                message += f"{i}. {item['name']}: {item['description']}\n"
                message += f"   Caught at attempt #{item['caught_at']} at {item['location']}\n"
        
        self.refresh_display(f"\n{message}")

    def show_kit_bag(self):
        """Display kit bag contents"""
        message = "\n--- HARVEY'S KIT BAG ---\n"
        for item_id, item in self.kit_bag.items():
            status = ""
            if item.get("consumable", False):
                uses = item.get("uses_remaining", 0)
                status = f" ({uses} uses remaining)" if uses > 0 else " (empty)"
            
            message += f"• {item['name']}{status}\n"
            message += f"  {item['description']}\n"
            
            if item_id == "thermos" and item.get("contents"):
                message += f"  Contains: {item['contents']['name']}\n"
            
            message += "\n"
        
        self.refresh_display(message)

    def drink_thermos(self):
        """Handle drinking from thermos"""
        if self.thermos_remaining <= 0:
            message = "Harvey's thermos is empty, leaving him to contemplate the philosophical implications of an empty vessel."
            self.refresh_display(f"\n{message}")
            return
        
        contents = self.thermos_contents
        self.thermos_remaining -= 1
        
        if contents['type'] == 'brandy':
            self.brandy_level += 1
            
            # First time discovering brandy
            if self.brandy_level == 1:
                message = "Harvey takes a sip expecting tea and discovers... BRANDY! His eyes widen in scholarly surprise. 'Good heavens! How did this get in here?'"
            else:
                brandy_messages = [
                    "Harvey takes another sip of brandy, feeling considerably more optimistic about his angling prospects.",
                    "The brandy warms Harvey's scholarly soul, making even the fish seem more cooperative.",
                    "Harvey reflects that brandy is excellent for both medicinal purposes and improving one's perspective on aquatic disappointment."
                ]
                message = random.choice(brandy_messages)
            
            # Apply brandy effects
            self.determination = min(100, self.determination + random.randint(8, 15))
            self.dignity = max(0, self.dignity - random.randint(2, 5))
            self.inspiration_level = min(100, self.inspiration_level + random.randint(5, 10))
            
        else:  # Tea
            tea_messages = [
                f"Harvey enjoys a proper cup of {contents['name']}, restoring his British composure.",
                f"The {contents['name']} works wonders for Harvey's determination and dignity.",
                f"Harvey reflects that {contents['name']} is the solution to most of life's problems, including recalcitrant fish."
            ]
            message = random.choice(tea_messages)
            
            self.determination = min(100, self.determination + random.randint(5, 10))
            self.dignity = min(100, self.dignity + random.randint(3, 8))
        
        # Apply brandy effects to message if applicable
        if self.brandy_level > 0:
            message = self.apply_brandy_effects(message)
        
        self.refresh_display(f"\n{message}")

    def load_locations(self):
        """Load location data from JSON file"""
        try:
            if os.path.exists('locations_data.json'):
                with open('locations_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('locations', [])
            else:
                return self.get_fallback_locations()
        except json.JSONDecodeError as e:
            print(f"Error loading locations_data.json: {e}")
            return self.get_fallback_locations()

    def get_fallback_locations(self):
        """Fallback location data if JSON file is missing"""
        return [
            {"name": "River Test, Hampshire", "type": "river", "key": "river_test", "difficulty": "challenging"},
            {"name": "River Itchen, Hampshire", "type": "river", "key": "river_itchen", "difficulty": "very challenging"},
            {"name": "River Nadder, Wiltshire", "type": "river", "key": "river_nadder", "difficulty": "moderate"},
            {"name": "Bewl Water, Kent", "type": "reservoir", "key": "bewl_water", "difficulty": "moderate"},
            {"name": "Chew Valley Lake, Somerset", "type": "reservoir", "key": "chew_reservoir", "difficulty": "challenging"},
            {"name": "River Kennet, Berkshire", "type": "river", "key": "river_kennet", "difficulty": "challenging"}
        ]

    def select_random_location(self):
        """Randomly select a fishing location for this game session"""
        if self.locations_data:
            return random.choice(self.locations_data)
        else:
            return self.get_fallback_locations()[0]

    def show_location_info(self):
        """Display detailed information about the current location"""
        location = self.location_data
        print(f"\n📍 LOCATION: {location['name']}")
        print(f"🌊 Type: {location['type'].title()}")
        
        if 'description' in location:
            print(f"📝 Description: {location['description']}")
        
        if 'difficulty' in location:
            difficulty_emoji = {
                'easy': '🟢',
                'moderate': '🟡', 
                'challenging': '🟠',
                'very challenging': '🔴',
                'expert': '⚫'
            }
            emoji = difficulty_emoji.get(location['difficulty'], '❓')
            print(f"⚡ Difficulty: {emoji} {location['difficulty'].title()}")
        
        if 'fish_types' in location:
            fish_list = ', '.join(location['fish_types'])
            print(f"🐟 Fish Species: {fish_list}")

    def load_responses(self):
        """Load all response data from JSON files"""
        responses = {}
        response_files = [
            'responses_basic.json',
            'responses_silly.json', 
            'responses_environmental.json',
            'responses_locations.json',
            'responses_harvey_torbett.json',
            'responses_game_text.json'
        ]
        
        for filename in response_files:
            try:
                if os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        responses.update(file_data)
            except json.JSONDecodeError as e:
                print(f"Error loading {filename}: {e}")
                
        return responses

    def get_random_response(self, category, subcategory=None):
        """Get a random response from the loaded data"""
        try:
            if subcategory:
                responses = self.responses.get(category, {}).get(subcategory, [])
            else:
                responses = self.responses.get(category, [])
            
            if responses:
                return random.choice(responses)
            else:
                return {"text": f"No responses found for {category}/{subcategory}", "effects": {}}
        except Exception as e:
            return {"text": f"Error getting response: {e}", "effects": {}}

    def get_text(self, category, subcategory=None):
        """Get text from responses without random selection"""
        try:
            if subcategory:
                return self.responses.get(category, {}).get(subcategory, f"Missing text: {category}/{subcategory}")
            else:
                return self.responses.get(category, f"Missing text: {category}")
        except Exception as e:
            return f"Error getting text: {e}"

    def apply_effects(self, effects):
        """Apply stat changes from responses"""
        for stat, change in effects.items():
            if hasattr(self, stat):
                current_value = getattr(self, stat)
                if isinstance(current_value, (int, float)):
                    new_value = max(0, min(100, current_value + change))
                    setattr(self, stat, new_value)
                else:
                    setattr(self, stat, change)

    def clear_terminal(self):
        """Clear terminal screen cross-platform"""
        os.system('cls' if os.name == 'nt' else 'clear')
        return

    def get_status_display(self):
        """Generate the persistent status display"""
        # Determine status indicators
        determination_icon = '💀' if self.determination < 20 else '⚠️' if self.determination < 50 else '✅'
        dignity_icon = '💀' if self.dignity < 20 else '⚠️' if self.dignity < 50 else '✅'
        chaos_icon = '🔥' if self.mishap_level >= 4 else '⚠️' if self.mishap_level >= 2 else '✅'
        
        # Create compact status line
        status_line = (
            f"🎣 Harvey Torbett at {self.location} | "
            f"Attempts: {self.attempts} | Fish: {self.fish_caught} | "
            f"Det: {self.determination}%{determination_icon} | "
            f"Dig: {self.dignity}%{dignity_icon} | "
            f"Chaos: {self.mishap_level}/{self.max_mishap_level}{chaos_icon} | "
            f"Acad: {self.academic_reputation}% | "
            f"Insp: {self.inspiration_level}%"
        )
        
        # Create gear status line
        gear_line = (
            f"🎣 Rod: {'✅' if self.rod_attached else '❌'} | "
            f"🪰 Fly: {'✅' if self.fly_attached else '❌'} | "
            f"🥪 Sandwich: {self.sandwich_status} | "
            f"👢 Waders: {self.waders_status} | "
            f"🎩 Hat: {self.hat_status}"
        )
        
        return status_line, gear_line

    def display_status_header(self):
        """Display the persistent status at the top of the screen"""
        status_line, gear_line = self.get_status_display()
        
        # Get terminal width for proper formatting
        try:
            terminal_width = os.get_terminal_size().columns
        except:
            terminal_width = 80  # fallback
        
        # Create separator line
        separator = "=" * min(terminal_width, len(status_line))
        
        print(separator)
        print(status_line)
        print(gear_line)
        print(separator)
        print()  # Empty line for spacing

    def refresh_display(self, message=""):
        """Clear screen and redisplay status with optional message"""
        self.clear_terminal()
        self.display_status_header()
        if message:
            print(message)

    def execute_response(self, response):
        """Execute a response and apply its effects with status refresh"""
        if response:
            # Store the message
            message = f"\n{response['text']}"
            self.apply_effects(response.get('effects', {}))
            
            # Apply brandy effects if applicable
            if self.brandy_level > 0:
                message = self.apply_brandy_effects(message)
            
            # Refresh display with the message
            self.refresh_display(message)

    def add_automatic_scholarly_moment(self):
        """Occasionally add a Harvey scholarly moment after actions"""
        if random.random() < 0.3:  # 30% chance
            self.add_harvey_reaction()

    def add_harvey_reaction(self):
        """Add a random Harvey Torbett reaction based on current state"""
        if self.determination < 30:
            reaction_type = "philosophical_acceptance"
        elif self.mishap_level >= 3:
            reaction_type = "scholarly_excitement"
        else:
            reaction_type = "mild_frustration"
            
        reaction = self.get_random_response("harvey_reactions", reaction_type)
        if reaction:
            message = f"\n💭 {reaction['text']}"
            if self.brandy_level > 0:
                message = self.apply_brandy_effects(message)
            print(message)
            self.apply_effects(reaction.get('effects', {}))

    def random_quote(self):
        """Harvey shares wisdom from his extensive bibliography"""
        quote_type = random.choice(["fishing_wisdom", "non_fishing_wisdom", "literary_observations"])
        quote = self.get_random_response("harvey_quotes", quote_type)
        if quote:
            message = f"\n📚 Harvey reflects: \"{quote['text']}\""
            if self.brandy_level > 0:
                message = self.apply_brandy_effects(message)
            print(message)
            self.apply_effects(quote.get('effects', {}))
            self.inspiration_level = min(100, self.inspiration_level + 5)

    def give_lecture(self):
        """Harvey delivers an impromptu academic lecture"""
        academic_moment = self.get_random_response("harvey_academic_moments")
        if academic_moment:
            message = f"\n🎓 {academic_moment['text']}"
            if self.brandy_level > 0:
                message = self.apply_brandy_effects(message)
            print(message)
            self.apply_effects(academic_moment.get('effects', {}))
            self.academic_reputation = max(0, min(100, self.academic_reputation + random.randint(-5, 10)))

    def take_notes(self):
        """Harvey makes scholarly observations"""
        notes = self.get_text("notes")
        if isinstance(notes, list):
            note = random.choice(notes)
        else:
            # Fallback notes if not in data files
            fallback_notes = [
                "You carefully document the precise angle of that last catastrophic cast for your upcoming paper on 'Geometric Failures in Fly Fishing.'",
                "Harvey sketches the trajectory of his fly line, noting its remarkable resemblance to a Fibonacci spiral gone horribly wrong.",
                "You make detailed notes about the apparent intelligence of local waterfowl, wondering if they're suitable subjects for your next behavioral study.",
                "Harvey records the exact time and weather conditions, building a comprehensive database of 'Optimal Conditions for Angling Disasters.'",
                "You begin drafting a footnote for your next book about the philosophical implications of fishing in a universe that clearly has other plans."
            ]
            note = random.choice(fallback_notes)
        
        message = f"\n📝 {note}"
        if self.brandy_level > 0:
            message = self.apply_brandy_effects(message)
        print(message)
        self.inspiration_level = min(100, self.inspiration_level + 8)
        self.determination += 3

    def show_bibliography(self):
        """Display Harvey's impressive body of work"""
        biblio_text = f"""
{"=" * 60}
     THE COLLECTED WORKS OF HARVEY DOUGLAS LOUIS TORBETT
{"=" * 60}

📚 ANGLING LITERATURE:
"""
        fishing_books = self.responses.get("harvey_books", {}).get("fishing_titles", [])
        if not fishing_books:
            # Fallback books if not in data files
            fishing_books = [
                "The Philosophical Angler: Meditations on Mayflies and Mortality",
                "Chalk Stream Chronicles: A Gentleman's Guide to Aquatic Disappointment",
                "The Zen of Fly Fishing: Finding Inner Peace Through Outer Chaos",
                "Trout Psychology: Understanding the Piscine Mind"
            ]
        
        for i, book in enumerate(fishing_books, 1):
            biblio_text += f"   {i}. {book}\n"
            
        biblio_text += "\n📖 GENERAL SCHOLARSHIP:\n"
        other_books = self.responses.get("harvey_books", {}).get("non_fishing_titles", [])
        if not other_books:
            # Fallback books if not in data files
            other_books = [
                "A Gentleman's Guide to Competitive Croquet",
                "The Etiquette of Afternoon Tea in Unusual Circumstances",
                "Morris Dancing: A Sociological Study",
                "The Psychology of Queue Formation"
            ]
        
        for i, book in enumerate(other_books, 1):
            biblio_text += f"   {i}. {book}\n"
            
        biblio_text += f"""
🏆 Current Academic Reputation: {self.academic_reputation}%
💡 Inspiration Level: {self.inspiration_level}%
"""
        
        if self.brandy_level > 0:
            biblio_text = self.apply_brandy_effects(biblio_text)
        
        self.refresh_display(biblio_text)

    def contemplate(self):
        """Harvey engages in deep philosophical thought"""
        contemplations = self.get_text("contemplations")
        if isinstance(contemplations, list):
            thought = random.choice(contemplations)
        else:
            # Fallback contemplations if not in data files
            fallback_contemplations = [
                "You ponder the existential implications of a universe where fish appear to have better tactical awareness than most military strategists.",
                "Harvey contemplates whether his fishing failures are actually a form of performance art, and if so, whether he should be charging admission.",
                "You reflect on the possibility that you're not fishing for trout at all, but rather being fished for by some cosmic angler with a sense of irony.",
                "Harvey considers the philosophical question: If a fly fisher casts in a river and no one witnesses the resulting chaos, did it really happen?"
            ]
            thought = random.choice(fallback_contemplations)
        
        message = f"\n🤔 {thought}"
        if self.brandy_level > 0:
            message = self.apply_brandy_effects(message)
        print(message)
        self.determination += random.randint(5, 15)
        self.inspiration_level = min(100, self.inspiration_level + 10)

    def theorize(self):
        """Harvey develops new academic theories"""
        theories = self.get_text("theories")
        if isinstance(theories, list):
            theory = random.choice(theories)
        else:
            # Fallback theories if not in data files
            fallback_theories = [
                "You begin formulating the 'Torbett Principle': The probability of angling success is inversely proportional to the number of witnesses present.",
                "Harvey develops his 'Chaos Theory of Fly Fishing': Every cast exists in a superposition of success and disaster until observed by a trout.",
                "You theorize that rivers possess a collective consciousness that communicates fishing conditions to all aquatic life via some form of underwater internet.",
                "Harvey proposes the 'Conservation of Angling Dignity': Dignity can neither be created nor destroyed, only transferred from angler to fish."
            ]
            theory = random.choice(fallback_theories)
        
        message = f"\n🧠 {theory}"
        if self.brandy_level > 0:
            message = self.apply_brandy_effects(message)
        print(message)
        self.academic_reputation = min(100, self.academic_reputation + random.randint(5, 15))
        self.inspiration_level = min(100, self.inspiration_level + 12)
        self.determination += 8

    # Basic fishing actions
    def attach_rod(self):
        if self.rod_attached:
            message = "\nYour rod is already assembled, though it's looking rather skeptical about the whole enterprise."
            if self.brandy_level > 0:
                message = self.apply_brandy_effects(message)
            self.refresh_display(message)
            self.add_automatic_scholarly_moment()
            return
            
        # Improved success rate: 80% (was 70%)
        if random.random() < 0.8:
            response = self.get_random_response("attach_rod", "success")
            self.execute_response(response)
            self.rod_attached = True
            self.track_success()
        else:
            response = self.get_random_response("attach_rod", "mishaps")
            self.execute_response(response)
            self.escalate_chaos()
        
        self.add_automatic_scholarly_moment()

    def attach_fly(self):
        if self.fly_attached:
            response = self.get_random_response("attach_fly", "already_attached")
            self.execute_response(response)
            self.add_automatic_scholarly_moment()
            return
            
        # Improved success rate: 75% (was 60%)
        if random.random() < 0.75:
            response = self.get_random_response("attach_fly", "success")
            self.execute_response(response)
            self.fly_attached = True
            self.track_success()
        else:
            response = self.get_random_response("attach_fly", "mishaps")
            self.execute_response(response)
            self.escalate_chaos()
        
        self.add_automatic_scholarly_moment()

    def cast_rod(self):
        if not self.rod_attached:
            response = self.get_random_response("cast_rod", "no_rod")
            self.execute_response(response)
            return
            
        if not self.fly_attached:
            response = self.get_random_response("cast_rod", "no_fly")
            self.execute_response(response)
            return
            
        self.attempts += 1
        
        # Improved success chance!
        base_chance = 0.5  # 50% base instead of 30%
        chaos_penalty = self.mishap_level * 0.02  # Reduced penalty (was 0.03)
        success_bonus = self.successful_actions * 0.02  # Bonus for successful actions
        
        success_chance = max(0.2, base_chance - chaos_penalty + success_bonus)  # Min 20% instead of 10%
        
        if random.random() < success_chance:
            # Successful cast!
            success_messages = [
                "🎣 Miraculous! Harvey executes a perfect cast, the line unfurling like poetry in motion!",
                "🎣 Extraordinary! The fly lands with the delicacy of a butterfly kiss upon the water's surface!",
                "🎣 Success! Harvey's academic approach to angling finally bears fruit!",
                "🎣 Splendid! The cast arcs gracefully through the air, landing exactly where Harvey intended!",
                "🎣 Brilliant! Harvey's scholarly precision pays off with a textbook-perfect cast!"
            ]
            message = f"\n{random.choice(success_messages)}"
            if self.brandy_level > 0:
                message = self.apply_brandy_effects(message)
            print(message)
            self.cast_made = True
            self.track_success()
            self.inspiration_level = min(100, self.inspiration_level + 15)
            return
    

        
        # Determine mishap category based on chaos level (now with more levels)
        if self.mishap_level <= 2:
            mishap_category = "early_mishaps"
        elif self.mishap_level <= 5:
            mishap_category = "medium_mishaps"
        else:
            mishap_category = "late_mishaps"
            
        response = self.get_random_response("cast_rod", mishap_category)
        self.execute_response(response)
        self.escalate_chaos()

    def reel_in(self):
        if not self.cast_made:
            response = self.get_random_response("reel_in", "no_cast")
            self.execute_response(response)
            return
        
        # Chance of actually catching something!
        catch_chance = 0.15 + (self.successful_actions * 0.02)
        
        if random.random() < catch_chance:
            # Determine if it's a real fish or unusual item
            if random.random() < 0.6:  # 60% chance of real fish
                # Actually caught a fish!
                fish_types = ["Brown Trout", "Rainbow Trout", "Grayling", "Pike", "Perch", "Roach", "Salmon", "Chub"]
                fish_name = random.choice(fish_types)
                
                catches = [
                    f"🐟 Extraordinary! A magnificent {fish_name.lower()} rises to your fly! Harvey's academic theories are vindicated!",
                    f"🐠 Success! A beautiful {fish_name.lower()} takes the bait, clearly impressed by Harvey's scholarly approach!",
                    f"🎣 Triumph! A {fish_name.lower()} of considerable intelligence has chosen to engage in this aquatic discourse!",
                    f"🐟 Victory! Harvey's persistence pays off with a splendid {fish_name.lower()} worthy of academic documentation!"
                ]
                message = f"\n{random.choice(catches)}"
                
                # Add fish to catch with proper name
                self.add_to_catch(fish_name, f"A magnificent {fish_name.lower()} caught through scholarly persistence")
                
                self.fish_caught += 1
                self.determination = min(100, self.determination + 20)
                self.dignity = min(100, self.dignity + 15)
                self.inspiration_level = min(100, self.inspiration_level + 25)
                self.academic_reputation = min(100, self.academic_reputation + 10)
                self.track_success()
                
            else:
                # Caught something unusual - use the interaction engine
                self.interaction_engine.add_unusual_catch()
                
            if self.brandy_level > 0:
                message = self.apply_brandy_effects(message)
            print(message)
            
            self.cast_made = False
        else:
            response = self.get_random_response("reel_in", "catches")
            self.execute_response(response)
            self.cast_made = False

    def eat_sandwich(self):
        if self.sandwich_status == "eaten":
            response = self.get_random_response("eat_sandwich", "already_eaten")
        elif self.sandwich_status == "soggy":
            response = self.get_random_response("eat_sandwich", "soggy")
        elif self.sandwich_status == "sentient":
            response = self.get_random_response("eat_sandwich", "sentient")
        else:
            response = self.get_random_response("eat_sandwich", "normal")
            
        self.execute_response(response)

    def wade_deeper(self):
        if self.waders_status == "intact":
            response = self.get_random_response("wade_deeper", "intact")
        elif self.waders_status == "leaking":
            response = self.get_random_response("wade_deeper", "leaking")
        else:
            response = self.get_random_response("wade_deeper", "flooded")
            
        self.execute_response(response)

    # Silly actions
    def whistle(self):
        response = self.get_random_response("silly_actions", "whistle")
        self.execute_response(response)

    def pray(self):
        response = self.get_random_response("silly_actions", "pray")
        self.execute_response(response)

    def curse(self):
        response = self.get_random_response("silly_actions", "curse")
        self.execute_response(response)

    def dance(self):
        response = self.get_random_response("silly_actions", "dance")
        self.execute_response(response)

    def sing(self):
        response = self.get_random_response("silly_actions", "sing")
        self.execute_response(response)

    def meditate(self):
        response = self.get_random_response("silly_actions", "meditate")
        self.execute_response(response)

    # Gear actions
    def tie_knot(self):
        response = self.get_random_response("gear_actions", "tie_knot")
        self.execute_response(response)

    def clean_glasses(self):
        response = self.get_random_response("gear_actions", "clean_glasses")
        self.execute_response(response)

    def adjust_hat(self):
        response = self.get_random_response("gear_actions", "adjust_hat")
        self.execute_response(response)

    def change_fly(self):
        response = self.get_random_response("gear_actions", "change_fly")
        self.execute_response(response)

    # Information commands
    def check_time(self):
        response = self.get_random_response("information", "check_time")
        self.execute_response(response)

    def check_weather(self):
        response = self.get_random_response("information", "check_weather")
        self.execute_response(response)

    def look_around(self):
        response = self.get_random_response("locations", self.location_data["key"])
        self.execute_response(response)

    def describe_location(self):
        response = self.get_random_response("locations", self.location_data["key"])
        self.execute_response(response)

    def check_gear(self):
        title = self.get_text("status_displays", {}).get("gear_title", "GEAR STATUS")
        print(f"\n--- {title} ---")
        print(f"🎣 Rod: {'Assembled' if self.rod_attached else 'Not assembled'}")
        print(f"🪰 Fly: {'Attached' if self.fly_attached else 'Not attached'}")
        print(f"🥪 Sandwich: {self.sandwich_status}")
        print(f"👢 Waders: {self.waders_status}")
        print(f"🎩 Hat: {self.hat_status}")
        print(f"🍵 Thermos: {self.thermos_remaining} servings of {self.thermos_contents['name']}")
        if self.brandy_level > 0:
            print(f"🥃 Brandy Level: {self.brandy_level}/6 ({self.get_brandy_modifier()['mood']})")

    def show_stats(self):
        """Display detailed stats with status refresh"""
        stats_text = f"""
{"=" * 50}
           HARVEY TORBETT DETAILED STATUS
{"=" * 50}
🎣 Fishing Attempts: {self.attempts}
🐟 Fish Caught: {self.fish_caught}
💪 Determination: {self.determination}% {'💀' if self.determination < 20 else '⚠️' if self.determination < 50 else '✅'}
🎩 Dignity: {self.dignity}% {'💀' if self.dignity < 20 else '⚠️' if self.dignity < 50 else '✅'}
🌪️ Chaos Level: {self.mishap_level}/{self.max_mishap_level} {'🔥' if self.mishap_level >= 4 else '⚠️' if self.mishap_level >= 2 else '✅'}
🎓 Academic Reputation: {self.academic_reputation}%
💡 Inspiration Level: {self.inspiration_level}%
🌤️ Weather: {self.weather}
🥪 Sandwich: {self.sandwich_status}
👢 Waders: {self.waders_status}
🎩 Hat: {self.hat_status}
🍵 Thermos: {self.thermos_remaining} servings remaining
"""
        
        if self.brandy_level > 0:
            stats_text += f"🥃 Brandy Level: {self.brandy_level}/6 ({self.get_brandy_modifier()['mood']})\n"
        
        stats_text += "=" * 50
        
        if self.brandy_level > 0:
            stats_text = self.apply_brandy_effects(stats_text)
        
        self.refresh_display(stats_text)

    def track_success(self):
        """Track successful actions to provide positive momentum"""
        self.successful_actions += 1
        self.consecutive_failures = 0
        
        # Small determination boost for success
        self.determination = min(100, self.determination + random.randint(2, 5))
        
        # Occasional Harvey celebration
        if self.successful_actions % 3 == 0:
            celebrations = [
                "Harvey adjusts his spectacles with satisfaction, making a mental note for his next paper.",
                "A moment of quiet triumph! Harvey's methodical approach shows promise.",
                "Harvey permits himself a small smile of scholarly satisfaction.",
                "Progress! Harvey's determination to apply academic rigor to angling bears fruit."
            ]
            message = f"\n✨ {random.choice(celebrations)}"
            if self.brandy_level > 0:
                message = self.apply_brandy_effects(message)
            print(message)

    def escalate_chaos(self):
        """Slower chaos escalation with more nuanced progression"""
        self.consecutive_failures += 1
        
        # Slower mishap level increase - only sometimes
        if random.random() < 0.6:  # 60% chance instead of always
            self.mishap_level = min(self.mishap_level + 1, self.max_mishap_level)
        
        # Reduced determination loss
        base_loss = random.randint(3, 8)  # Was 5-15
        # Extra loss for consecutive failures
        consecutive_penalty = min(self.consecutive_failures * 2, 10)
        total_loss = base_loss + consecutive_penalty
        
        self.determination -= total_loss
        
        # Reduced dignity loss
        dignity_loss = random.randint(2, 6)  # Was 3-10
        self.dignity -= dignity_loss
        
        # Ensure stats don't go below 0
        self.determination = max(0, self.determination)
        self.dignity = max(0, self.dignity)
        
        # Harvey gains inspiration from chaos (slightly reduced)
        inspiration_gain = random.randint(2, 5)  # Was 3-8
        self.inspiration_level = min(100, self.inspiration_level + inspiration_gain)
        
        # Add Harvey reaction (reduced frequency)
        if random.random() < 0.4:  # 40% chance instead of 60%
            self.add_harvey_reaction()
        
        # Random environmental chaos (reduced frequency)
        if random.random() < 0.2:  # 20% chance instead of 30%
            response = self.get_random_response("environmental", "random_events")
            if response:
                message = f"\n*** {response['text']} ***"
                if self.brandy_level > 0:
                    message = self.apply_brandy_effects(message)
                print(message)

    def give_up(self):
        give_up_texts = self.get_text("game_over", {}).get("give_up", [])
        if not give_up_texts:
            # Fallback give up text
            give_up_texts = [
                f"{self.player_name} packs up his gear with the dignity of a gentleman scholar.",
                "Perhaps today's experiences will make an excellent chapter in his next book...",
                f"Final inspiration level: {self.inspiration_level}%"
            ]
        
        for text in give_up_texts:
            if "{player_name}" in text:
                message = f"\n{text.format(player_name=self.player_name)}"
            elif "{inspiration_level}" in text:
                message = f"{text.format(inspiration_level=self.inspiration_level)}"
            else:
                message = f"\n{text}"
            
            if self.brandy_level > 0:
                message = self.apply_brandy_effects(message)
            print(message)
        
        self.game_over = True

    def show_help(self):
        """Enhanced help showing available commands"""
        help_text = "\n--- HARVEY TORBETT COMMAND REFERENCE ---\n"
        help_text += "Commands can be used as 'verb object' (e.g., 'drink thermos', 'cast rod')\n\n"
        
        help_text += "🎣 FISHING COMMANDS:\n"
        help_text += "  attach rod, attach fly, cast rod, reel in\n\n"
        
        help_text += "🎒 INVENTORY COMMANDS:\n"
        help_text += "  drink thermos, eat sandwich, examine [item]\n"
        help_text += "  kit/bag - show kit bag contents\n"
        help_text += "  catch - show current catch\n\n"
        
        help_text += "🎩 PERSONAL CARE:\n"
        help_text += "  adjust hat, clean glasses, wade deeper\n\n"
        
        help_text += "📚 SCHOLARLY ACTIVITIES:\n"
        help_text += "  quote, lecture, take notes, bibliography\n"
        help_text += "  contemplate, theorize\n\n"
        
        help_text += "ℹ️ INFORMATION:\n"
        help_text += "  look, stats, inventory, check weather, check time\n\n"
        
        help_text += "🎭 DESPERATION ACTIONS:\n"
        help_text += "  whistle, pray, curse, dance, sing, meditate\n\n"
        
        help_text += "🚪 EXIT:\n"
        help_text += "  quit, exit, give up\n"
        
        if self.brandy_level > 0:
            help_text = self.apply_brandy_effects(help_text)
        
        self.refresh_display(help_text)

    def game_loop(self):
        """Main game loop with sophisticated command parsing"""
        while not self.game_over:
            if self.determination <= 10:
                no_determination_text = "Harvey has lost all determination and sits down to write a strongly worded letter to The Times about the declining standards of modern fish."
                if self.brandy_level > 0:
                    no_determination_text = self.apply_brandy_effects(no_determination_text)
                self.refresh_display(f"\n{no_determination_text}")
                break
            # Add encouragement at low determination
            if self.determination <= 25 and random.random() < 0.3:
                encouragements = [
                    "Harvey pauses to consult his extensive notes, finding renewed purpose in his scholarly mission.",
                    "A moment of reflection reminds Harvey that even failure provides valuable data for his research.",
                    "Harvey's academic training kicks in - every setback is merely another data point to analyze.",
                    "The gentleman scholar takes a deep breath, remembering that persistence is the hallmark of good research."
                ]
                message = f"\n🌟 {random.choice(encouragements)}"
                if self.brandy_level > 0:
                    message = self.apply_brandy_effects(message)
                print(message)
                self.determination = min(100, self.determination + random.randint(5, 10))
                
            print("\nWhat would you like to do?")
            command = input("> ").lower().strip()
            
            self.execute_command(command)

    def start_game(self):
        intro = self.get_text("game_intro", {})
        if not intro:
            # Fallback intro if not in data files
            intro = {
                "title": "HARVEY TORBETT FLY FISHING SIMULATOR",
                "subtitle": "A Thoroughly British Angling Adventure",
                "tagline": "Featuring the Collected Wisdom of a Gentleman Scholar",
                "research_topic": "Advanced Techniques in Aquatic Disappointment"
            }
        
        print("=" * 70)
        print(f"         {intro['title']}")
        print(f"       {intro['subtitle']}")
        print(f"    {intro['tagline']}")
        print("=" * 70)
        print(f"\n🎣 Today's Adventure: {self.location} 🎣")
        print(f"📚 Current Research: '{intro['research_topic']}'")
        
        # Show thermos contents discovery
        contents = self.thermos_contents
        if contents['type'] == 'brandy':
            print(f"🍵 Harvey's thermos contains... {contents['name']}! (This should be interesting)")
        else:
            print(f"🍵 Harvey's thermos contains {contents['name']}")
        
        print()
        
        # Show location info
        self.show_location_info()
        
        # Opening Harvey quote
        opening_quote = self.get_random_response("harvey_quotes", "fishing_wisdom")
        if opening_quote:
            print(f"\n💭 Harvey muses: \"{opening_quote['text']}\"\n")
        
        self.look_around()
        self.show_stats()
        self.game_loop()

# Start the game
if __name__ == "__main__":
    game = FishingGame()
    game.start_game()
