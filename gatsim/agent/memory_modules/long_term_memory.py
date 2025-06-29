"""
File: long_term_memory.py
Description: Defines the core long-term memory module for generative agents.
**Long term memory is a collection of concept nodes**


# Store spatial-temporal information in long term memory, not separate "spatial memory"
storing your spatial-temporal information together with other types of information (e.g., personal events, chats, thoughts) in the same long-term memory structure, using a unified ConceptNode format — with extended fields like spatial_scope, time, duration, and tags.
1.	Unified Reflection & Retrieval:
    •	By storing all types of memories in the same structure, your agent can reflect on them collectively. For example, when an agent reflects on why they experienced a delay at the metro, it can correlate that spatial-temporal data with previous personal experiences or external events.
    •	It simplifies retrieval since your retrieval functions (using keywords, embeddings, etc.) can operate over the entire memory without needing separate pipelines.
2.	Cross-Modal Reasoning:
    •	Integrating spatial-temporal events with personal events and chats enables richer decision-making. The agent can use past experiences (e.g., delays at the metro, crowding at the coffee shop) to adjust its future behavior or plans.
    •	This can lead to more realistic and adaptive responses (e.g., "The metro was always delayed on Monday mornings; I should try a different mode of transport").
3.	Consistency and Scalability:
    •	A single, extensible ConceptNode class can be adapted to include additional fields (such as spatial_scope, time, or duration) while maintaining compatibility with your existing memory and reflection routines.
    •	This approach reduces the need for multiple memory systems, making the architecture simpler and easier to maintain.


# Concept node's spatial and temporal attributes 
Concept nodes can have spatial (spatial_scope) and temporal (time_scope) attributes; these attributes are optional. None if they cannot be specified.
Spatial temporal information are for transportation related memory retrieval. If no spatial-temporal information is provided, only keywords and semantic similarity will be used for retrieval.


# spatial_scope will be converted to spatial_coverage when doing spatial_temporal matching
spatial_coverage (list[str]): spatial_coverage property of the spatial_scope; a list of nodes or links or facilities;
    node, link, facility are the basic elements of the network;
    spatial_coverage is a list of links or facilities that are covered by the spatial_scope;
    None if the concept does not contain spatial information;


# Time scope attribute of concept node does not contain day of week information for simplicity
The extension of concept node definition to all time scope to have day of week property (like "Monday", "Weekday") is left for future work.


# Recency Score computation
Recency score is a measure of how recent the concept node is;
We use exponential decay (vs linear decay) for the recency score; it's a common and effective way to model the decreasing relevance of information over time.
recommend setting config.recency_decay to something like 0.9 or 0.95. This would mean:
A 1-day old memory has a recency score of 0.9 (or 0.95)
A 7-day old memory has a recency score of 0.48 (or 0.70)
A 30-day old memory has a recency score of 0.04 (or 0.21)
This gives you a balance where recent memories are strongly preferred, but older important memories can still be retrieved if they're particularly relevant or important.
"""
import json
import os
import copy
from datetime import datetime, timedelta, time
import faiss
import numpy as np
from gatsim import config
from gatsim.utils import pretty_print
from gatsim.agent.llm_modules.llm import get_embedding
from gatsim.agent.llm_modules.run_prompt import generate_importance_score



class ConceptNode: 
    """ 
    The ConceptNode class represents a node in an long term memory structure.     
    Concept node has "thought/event/chat" types;
    Reflections are of "thought" type.
    An instance of the ConceptNode class holds various properties that describe a piece of information (an event, thought, or chat) that the system stores in memory.
    """
    def __init__(self, type, created, content, keywords, spatial_scope, time_scope, importance, embedding=None, expiration=None):
        """
        Instance variables:
         - id (int): unique id
         - type (str): "event" | "chat" | "thought"
         - created (datetime): created time of the concept node; simulation time
         - last_accessed (datetime): last accessed time of the concept node
         - expiration (datetime): expiration time
         - content (str): memory content, e.g. "Link St_3_link_2 is congested during 8 AM - 9 AM."
         - keywords (list[str]): keywords for retrieval, e.g. ["St_3_link_2", "congestion", "morning"]
         - spatial_scope (list[str]): the spatial scope of the concept; a list of entity names; an entity name can be link_name, facility_name, road_name, maze_name.
            None if the concept does not contain spatial information;
         - time_scope (list[time]): time scope of the concept; a list of two elements; e.g. [time(8, 0), time(9,0)]
            None if the concept does not contain temporal information;
         - importance (float): importance score for sorting and filtering; 0.0 - 1.0
         - embedding (numpy array): embedding vector
        """
        self.id = int(datetime.now().strftime("%m%d%H%M%S%f"))  # id is generated based on current machine time; %S is seconds, %f is microseconds (6 digits); 
        self.type = type
        self.created = created  # datetime obj
        self.last_accessed = created  # datetime obj
        self.expiration = expiration  # datetime obj
        self.content = content
        self.keywords = keywords
        self.spatial_scope = spatial_scope  # a list of names
        self.time_scope = time_scope  # list of two time objs
        self.importance = max(0.0, min(1.0, importance))  # make sure importance is within [0.0, 1.0]
        self.embedding = embedding
        if embedding is None:
            self.embedding = get_embedding(self.content)
        if not expiration:
            self.expiration = self.compute_initial_expiration()
        
    def __str__(self):
        """String representation of the concept node."""
        spatial_info = f", spatial_scope: {self.spatial_scope}" if self.spatial_scope else ""
        temporal_info = f", time: {self.time_scope}" if self.time_scope else ""
        return f"ConceptNode(id={self.id}, type={self.type}, importance={self.importance:.2f}{spatial_info}{temporal_info}, content='{self.content[:50]}{'...' if len(self.content) > 50 else ''}')"


    def compute_initial_expiration(self) -> datetime:
        """
        Function to compute the initial expiration time of a concept node using a power function.
        Different concept types use different power values for non-linear importance scaling.
        """
        # Configuration for different concept types
        # You can adjust these values based on your needs
        
        # Get configuration for this concept type, default to "event" if type not found
        expiration_config = config.EXPIRATION_CONFIG.get(self.type, config.EXPIRATION_CONFIG["event"])
        min_hours = expiration_config["min_hours"]
        max_hours = expiration_config["max_hours"]
        power = expiration_config["power"]
        
        # Calculate coefficient c such that g(1) = max_hours - min_hours
        # g = c * (importance^power)
        # When importance = 1: g(1) = c * (1^power) = c
        # We want g(1) = max_hours - min_hours
        # Therefore: c = max_hours - min_hours
        lifespan_hours = min_hours + (max_hours - min_hours) * (self.importance ** power)
        lifespan = timedelta(hours=lifespan_hours)
        
        return self.created + lifespan


    def to_dict(self):
        """Convert the ConceptNode to a dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "created": self.created.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "expiration": self.expiration.isoformat() if self.expiration else None,
            "content": self.content,
            "keywords": self.keywords,
            "spatial_scope": self.spatial_scope,
            "time_scope": [t.isoformat() if t else None for t in self.time_scope] if self.time_scope else None,
            "importance": self.importance,
            "embedding": None #self.embedding.tolist() if isinstance(self.embedding, np.ndarray) else self.embedding
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a ConceptNode from a dictionary."""
        created = datetime.fromisoformat(data["created"])
        last_accessed = datetime.fromisoformat(data["last_accessed"])
        expiration = datetime.fromisoformat(data["expiration"]) if data["expiration"] else None
        time_scope = None
        if data["time_scope"]:
            time_scope = [time.fromisoformat(t) if t else None for t in data["time_scope"]]
        
        # Convert embedding back to numpy array if it's a list
        embedding = data["embedding"]
        if isinstance(embedding, list):
            embedding = np.array(embedding)
            
        concept_node = cls(
            type=data["type"],
            created=created,
            content=data["content"],
            keywords=data["keywords"],
            spatial_scope=data["spatial_scope"],
            time_scope=time_scope,
            importance=data["importance"],
            embedding=embedding,
            expiration=expiration,
        )
        # Note: embedding is not saved to disk; hence None
        # hence embedding will be regenerated here.
        concept_node.id = data["id"]
        concept_node.last_accessed = last_accessed
        return concept_node



def convert_concept_nodes_to_str(curr_time, purpose, concept_nodes):
    """
    Convert a list of concept nodes to a string representation
    
    Args:
        curr_time (datetime): current time
        purpose (str): The purpose of the concept nodes; "perceived" or "retrieved"
        concept_nodes (list): A list of concept nodes
    
    Returns:
        str: A string representation of the concept nodes
    """
    if purpose not in ["perceived", "retrieved"]:
        raise Exception("Value error")
    
    if purpose == "perceived":
        ans = """
The person has the following perception:
---CURRENT PERCEIVED SECTION START---"""
        if not concept_nodes:
            ans += "\n(empty)"
            return ans
    else:
        ans = """
The person retrieved the following concepts from personal long term memory:
---CURRENT RETRIEVED SECTION START---"""
        if not concept_nodes:
            ans += "\n(empty)"
            return ans
    
    # Group concept nodes by date
    from collections import defaultdict
    nodes_by_date = defaultdict(list)
    
    for node in concept_nodes:
        date_key = node.created.date()
        nodes_by_date[date_key].append(node)
    
    # Sort dates in reverse chronological order (newest first)
    sorted_dates = sorted(nodes_by_date.keys(), reverse=True)
    
    # Get today's date from curr_time
    today = curr_time.date()
    
    for date in sorted_dates:
        # Add date header
        if date == today:
            date_str = f"TODAY ({date.strftime('%A, %B %d, %Y')})"
        elif date == today - timedelta(days=1):
            date_str = f"YESTERDAY ({date.strftime('%A, %B %d, %Y')})"
        else:
            date_str = date.strftime('%A, %B %d, %Y').upper()
        
        if purpose == "retrieved":
            ans += f"\n\n{date_str}:"
        
        # Group nodes by type for this date
        events = []
        chats = []
        thoughts = []
        
        for node in nodes_by_date[date]:
            if node.type == "event":
                events.append(node)
            elif node.type == "chat":
                chats.append(node)
            elif node.type == "thought":
                thoughts.append(node)
        
        # Sort each type by time in reverse chronological order (newest first)
        events.sort(key=lambda x: x.created, reverse=True)
        chats.sort(key=lambda x: x.created, reverse=True)
        thoughts.sort(key=lambda x: x.created, reverse=True)
        
        # Add events
        if events:
            ans += "\n\n**EVENTS**"
            for node in events:
                ans += f"\n[{node.created.strftime('%H:%M')}] {node.content}"
        
        # Add chats
        if chats:
            ans += "\n\n**CHATS**"
            for node in chats:
                ans += f"\n[{node.created.strftime('%H:%M')}] {node.content}"
        
        # Add thoughts
        if thoughts:
            ans += "\n\n**THOUGHTS**"
            for node in thoughts:
                ans += f"\n[{node.created.strftime('%H:%M')}] {node.content}"
    
    if purpose == "perceived":
        ans += "\n---CURRENT PERCEIVED SECTION END---"
    else:
        ans += "\n---CURRENT RETRIEVED SECTION END---"
    
    return ans


def convert_concept_tuple_to_concept_node(persona, maze, concept_tuple):
    """ 
    Convert concept tuple to ConceptNode
    Concept tuple format:
        [<content>, <keywords>, <spatial_scope>, <time_scope>]
         - content (str): memory content, e.g. "Link St_3_link_2 is congested during 8 AM - 9 AM."
         - keywords (str): keywords for retrieval, e.g. "St_3_link_2, congestion, morning"
         - spatial_scope (str): the spatial scope of the concept; spatial_scope (str): entities (link_name, facility_name, road_name, maze_name) separated by the comma.
            None if the concept does not contain spatial information;
         - time_scope (str): time scope of the concept; e.g. "11:00-14:00"
            None if the concept does not contain temporal information;
            
    Returns:
        a list of concept nodes
    """
    type = "thought"
    content = concept_tuple[0]
    keywords = [k.strip() for k in concept_tuple[1].split(',')]  # keywords
    importance = generate_importance_score(persona, maze, type, content)
    if concept_tuple[2] == "none":
        spatial_scope = []
    else:
        spatial_scope = [k.strip() for k in concept_tuple[2].split(',')]  # spatial scope; convert str to list
    time_span = concept_tuple[3]
    if ',' in time_span:
        # if there are more than one intervals, e.g. 11:00-13:00, 14:00-16:00
        time_spans = [k.strip() for k in time_span.split(',')]
    else:
        time_spans = [time_span]
    
    concept_nodes = []
    for time_span in time_spans:
        time_scope = None
        if time_span != "none":
            try:
                start, end = time_span.split("-")
                start = datetime.strptime(start, "%H:%M").time()
                end = datetime.strptime(end, "%H:%M").time()
                time_scope = [start, end]
            except:
                # failsafe
                pretty_print(f"Error 012: {persona.name} has an invalid time_scope: {time_scope}", 2)
                time_scope = None
        #time_scope = convert_time_scope_str_to_datetime(persona.st_mem.curr_time, concept_tuple[3])
        concept_node = ConceptNode(type, persona.st_mem.curr_time, content, keywords, spatial_scope, time_scope, importance)
        concept_nodes.append(concept_node)
    return concept_nodes





class LongTermMemory: 
    """ 
    The LongTermMemory class is a memory structure used to manage different types of concepts (events, thoughts, and chats) for a persona in the system. 
    It organizes and stores these concepts and supports various methods for adding, retrieving, and saving them. 
    """
    def __init__(self, persona_folder): 
        self.persona_folder = persona_folder
        self.curr_time = datetime.strptime(config.start_date, "%Y-%m-%d %H:%M:%S")
        
        self.id_to_concept_node = dict()  # A dictionary that maps node IDs to their respective ConceptNode instances. This provides direct access to any specific concept stored in memory by its ID.

        # for sequential retrieval
        self.seq_event_ids = []  # A list of node ids that holds the events added to memory. stored in the order they are added.
        self.seq_thought_ids = []  # A list of node ids that holds the thoughts added to memory, stored in the order of addition.
        self.seq_chat_ids = []  # A list of node ids that holds chat-related concepts stored in memory, stored in the order of addition.
        self.seq_concept_ids  = []  # A list of node ids that holds all nodes (events, thoughts, chats) added to memory. This is a comprehensive list of all concepts stored in memory.
        
        # for keyword-based retrieval
        self.kw_to_event_ids = dict()  # A dictionary that maps keywords to lists of event ids. This is used to quickly find events related to specific keywords.
        self.kw_to_thought_ids = dict()  # A dictionary that maps keywords to lists of thought ids. Similar to kw_to_event, it allows quick retrieval of thoughts by keyword.
        self.kw_to_chat_ids = dict()  # A dictionary that maps keywords to lists of chat ids. This provides fast access to chat-related concepts by keyword.
        self.kw_to_concept_ids = dict()
        
        # for similarity search
        self.vs_index = faiss.IndexFlatL2(384)  # vectorstore index; for similarity search; adjust to model dim if needed
        self.vs_id_to_concept_id = {}  # maps vectorstore index to ConceptNode.id
        
        # record the contents of added nodes; to avoid redundant addition of perceived nodes to memory.
        self.concept_contents = []
        self.concept_content_to_id = {}
        
        
    def load(self, persona_folder=None):
        """ 
        Load the long term memory from persona folder.
        
        Args:
            persona_folder (str): The path to the folder containing the long term memory.
        
        Returns:
            None
        """
        if persona_folder is None:
            persona_folder = self.persona_folder
        
        memory_path = os.path.join(persona_folder, "long_term_memory.json")
        if not os.path.exists(memory_path):
            return  # No memory file exists yet
        
        with open(memory_path, 'r') as f:
            lt_mem_save = json.load(f)
            
        self.curr_time = datetime.strptime(lt_mem_save['curr_time'], "%Y-%m-%d %H:%M:%S")
        data = lt_mem_save['concept_nodes']
            
        # Reset current memory structures
        self.id_to_concept_node.clear()
        self.seq_event_ids.clear()
        self.seq_thought_ids.clear()
        self.seq_chat_ids.clear()
        self.seq_concept_ids.clear()
        self.kw_to_event_ids.clear()
        self.kw_to_thought_ids.clear()
        self.kw_to_chat_ids.clear()
        self.kw_to_concept_ids.clear()
        
        # Reset vectorstore index
        self.vs_index = faiss.IndexFlatL2(384)
        self.vs_id_to_concept_id.clear()
        
        # Load nodes
        for concept_data in data:
            concept_node = ConceptNode.from_dict(concept_data)
            # Note: embedding is already regenerated in ConceptNode.__init__ when embedding=None!!
            self.add_concept_node(concept_node, build_index=False)
        
        # Rebuild the vectorstore index
        if self.id_to_concept_node:
            embeddings = []
            ids = []
            for vs_id, concept_id in enumerate(self.seq_concept_ids):
                concept = self.id_to_concept_node[concept_id]
                embeddings.append(concept.embedding)
                self.vs_id_to_concept_id[vs_id] = concept_id
            
            if embeddings:
                self.vs_index.add(np.array(embeddings))
            
    
    def save(self, persona_folder=None): 
        """
        Save the long term memory to persona folder.
        Note: we only save the nodes in memory to the json file.
        when loading, we invoke add_concept_node() to add nodes to memory.
        
        Args:
            persona_folder (str): The path to the folder containing the long term memory.
        
        Returns:
            None
        """
        if persona_folder is None:
            persona_folder = self.persona_folder
            
        # Create the folder if it doesn't exist
        os.makedirs(persona_folder, exist_ok=True)
        
        memory_path = os.path.join(persona_folder, "long_term_memory.json")
        
        # Convert concept nodes to dictionaries
        concepts_data = [self.id_to_concept_node[concept_id].to_dict() for concept_id in self.seq_concept_ids]
        
        lt_mem_save = {}
        lt_mem_save['curr_time'] = self.curr_time.strftime("%Y-%m-%d %H:%M:%S")
        lt_mem_save['concept_nodes'] = concepts_data
        
        with open(memory_path, 'w') as f:
            json.dump(lt_mem_save, f, indent=4)
                

    
    def clean_up_memory(self):
        """ 
        Remove expired nodes from long term memory to save space.
        Vectorstore will be updated accordingly.
        Instance sequences and dicts will be updated accordingly.
        This is done sporadically.
        """
        
        if len(self.id_to_concept_node) < config.lt_mem_max_size:
            # No need to clean up if memory is not full
            return
        
        # Get IDs of expired nodes
        expired_ids = []
        for concept_id, concept_node in self.id_to_concept_node.items():
            if concept_node.expiration and concept_node.expiration < self.curr_time:
                expired_ids.append(concept_id)

        if not expired_ids:
            return  # No expired nodes, nothing to clean
        
        pretty_print()
        pretty_print(f"clean up {self.persona_folder}...", 2)
        # Remove expired nodes from all data structures
        for concept_id in expired_ids:
            concept_node = self.id_to_concept_node[concept_id]
            
            # Remove from sequence lists
            if concept_id in self.seq_concept_ids :
                self.seq_concept_ids.remove(concept_id)
            
            if concept_node.type == "event" and concept_id in self.seq_event_ids:
                self.seq_event_ids.remove(concept_id)
            elif concept_node.type == "thought" and concept_id in self.seq_thought_ids:
                self.seq_thought_ids.remove(concept_id)
            elif concept_node.type == "chat" and concept_id in self.seq_chat_ids:
                self.seq_chat_ids.remove(concept_id)
            
            # Remove from keyword dictionaries
            for kw in concept_node.keywords:
                kw_lower = kw.lower()
                
                if kw_lower in self.kw_to_concept_ids and concept_id in self.kw_to_concept_ids[kw_lower]:
                    self.kw_to_concept_ids[kw_lower].remove(concept_id)
                
                if concept_node.type == "event" and kw_lower in self.kw_to_event_ids and concept_id in self.kw_to_event_ids[kw_lower]:
                    self.kw_to_event_ids[kw_lower].remove(concept_id)
                elif concept_node.type == "thought" and kw_lower in self.kw_to_thought_ids and concept_id in self.kw_to_thought_ids[kw_lower]:
                    self.kw_to_thought_ids[kw_lower].remove(concept_id)
                elif concept_node.type == "chat" and kw_lower in self.kw_to_chat_ids and concept_id in self.kw_to_chat_ids[kw_lower]:
                    self.kw_to_chat_ids[kw_lower].remove(concept_id)
            
            # Remove from id_to_concept_node
            del self.id_to_concept_node[concept_id]
        
        # Rebuild the vectorstore index
        self.vs_index = faiss.IndexFlatL2(384)
        self.vs_id_to_concept_id.clear()
        
        if self.seq_concept_ids :
            embeddings = []
            for vs_id, concept_id in enumerate(self.seq_concept_ids ):
                concept_node = self.id_to_concept_node[concept_id]
                embeddings.append(concept_node.embedding)
                self.vs_id_to_concept_id[vs_id] = concept_id
            
            if embeddings is not None:
                self.vs_index.add(np.array(embeddings))


    def add_concept_node(self, concept_node, build_index=True):
        """ 
        Add concept node to long term memory.
        
        Args:
            concept_node (ConceptNode): The concept node to add.
            build_index (bool): Whether to rebuild the vector index.
        
        Returns:
            None
        """
        with config.lock:
            # Thread-safe version - ALWAYS waits for the lock.
            # so that we don't have to worry about race conditions.
            if concept_node.content in self.concept_contents[- (config.retention * 2):]:
                # if node already exists
                # e.g. broadcast news, you always get the broadcast news as long as it's not over
                # mark the old node as expired
                # add this new node
                old_id = self.concept_content_to_id[concept_node.content]
                old_concept_node = self.id_to_concept_node[old_id]
                old_concept_node.expiration = min(old_concept_node.expiration, self.curr_time - timedelta(minutes=config.minutes_per_step))  
                # mark old node as already expired if not expired
            
            # Add to id_to_concept_node dictionary
            self.id_to_concept_node[concept_node.id] = concept_node
            
            # Add to sequence lists
            self.seq_concept_ids.append(concept_node.id)
            
            if concept_node.type == "event":
                self.seq_event_ids.append(concept_node.id)
            elif concept_node.type == "thought":
                self.seq_thought_ids.append(concept_node.id)
            elif concept_node.type == "chat":
                self.seq_chat_ids.append(concept_node.id)
            
            # Add to keyword dictionaries
            for kw in concept_node.keywords:
                kw_lower = kw.lower()
                
                # Add to kw_to_concept_ids
                if kw_lower not in self.kw_to_concept_ids:
                    self.kw_to_concept_ids[kw_lower] = []
                self.kw_to_concept_ids[kw_lower].append(concept_node.id)
                
                # Add to type-specific keyword dictionaries
                if concept_node.type == "event":
                    if kw_lower not in self.kw_to_event_ids:
                        self.kw_to_event_ids[kw_lower] = []
                    self.kw_to_event_ids[kw_lower].append(concept_node.id)
                elif concept_node.type == "thought":
                    if kw_lower not in self.kw_to_thought_ids:
                        self.kw_to_thought_ids[kw_lower] = []
                    self.kw_to_thought_ids[kw_lower].append(concept_node.id)
                elif concept_node.type == "chat":
                    if kw_lower not in self.kw_to_chat_ids:
                        self.kw_to_chat_ids[kw_lower] = []
                    self.kw_to_chat_ids[kw_lower].append(concept_node.id)
            
            # Add to vectorstore for similarity search
            if build_index:
                vs_id = len(self.vs_id_to_concept_id)
                self.vs_id_to_concept_id[vs_id] = concept_node.id
                self.vs_index.add(np.array([concept_node.embedding]))
            
            self.concept_contents.append(concept_node.content)
            self.concept_content_to_id[concept_node.content] = concept_node.id


    def get_last_chat(self, target_persona_name): 
        """
        Get the last chat with the target persona.
        
        Args:
            target_persona_name (str): The name of the target persona.
            
        Returns:
            The last chat with the target persona, or None if no chat found.
        """
        target_name_lower = target_persona_name.lower()
        if target_name_lower in self.kw_to_chat_ids and self.kw_to_chat_ids[target_name_lower]: 
            id = self.kw_to_chat_ids[target_name_lower][-1]
            return self.id_to_concept_node[id]
        else: 
            return None
    
    
    def retrieve_by_keywords(self, keywords, retention=None):
        """
        Retrieve concepts from long term memory based on keyword matching.
        score = relevance_weight * keywords_matching_score + importance_weight * importance_score + recency_weight * recency_score
        Each component is normalized to the range [0, 1], and you can tune the weights.
        Note: 
        retrieve only active concepts (those no expiration date in the future)
        
        Args:
            keywords (list[str]): The keywords to search for.
            retention (int): The number of relevant events to retrieve.

        Returns:
            A list of (score, node) tuples sorted by score.
        """
        if retention is None:
            retention = config.retention
            
        # Configure weights
        relevance_weight = config.relevance_weight
        importance_weight = config.importance_weight
        recency_weight = config.recency_weight
        
        # Get concept nodes that match any of the keywords
        matching_concept_ids = set()
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in self.kw_to_concept_ids:
                matching_concept_ids.update(self.kw_to_concept_ids[kw_lower])
        
        # Calculate scores for each matching concept node
        scored_concept_nodes = []
        now = self.curr_time
        
        for concept_id in matching_concept_ids:
            concept_node = self.id_to_concept_node[concept_id]
            
            # Skip expired nodes
            if concept_node.expiration and concept_node.expiration < now:
                continue
            
            # Calculate keyword matching score (proportion of keywords that match)
            # Jaccard Similarity is used for keywords matching.
            keywords_lower = set(kw.lower() for kw in keywords)
            node_keywords_lower = set(kw.lower() for kw in concept_node.keywords)
            intersection = keywords_lower & node_keywords_lower
            union = keywords_lower | node_keywords_lower
            keywords_matching_score = len(intersection) / len(union) if union else 0

            if False:
                keywords_lower = [kw.lower() for kw in keywords]
                node_keywords_lower = [kw.lower() for kw in concept_node.keywords]
                matches = sum(1 for kw in keywords_lower if kw in node_keywords_lower)
                keywords_matching_score = matches / len(keywords)
            
            # Importance score is already normalized between 0 and 1
            importance_score = concept_node.importance
            
            # Calculate recency score (newer is better)
            age = now - concept_node.created
            recency_score = config.recency_decay **(age.total_seconds() /  3600 / 24)  # exponential decay    vs max(0, 1 - (age / max_age)) linear decay
            
            # Calculate final score
            score = (
                relevance_weight * keywords_matching_score +
                importance_weight * importance_score +
                recency_weight * recency_score
            )
            
            scored_concept_nodes.append((score, concept_node))
        
        # Sort by score (highest first) and limit to retention
        scored_concept_nodes.sort(key=lambda x: x[0], reverse=True)
        return scored_concept_nodes[:retention]
    
    
    def retrieve_by_similarity(self, content, retention=None):
        """
        Retrieve concepts from long term memory based on semantic similarity.
        score = relevance_weight * similarity_score + importance_weight * importance_score + recency_weight * recency_score
        Each component is normalized to the range [0, 1], and you can tune the weights.
        Note: 
        1) retrieve only active concepts (those with expiration date in the future)
        
        Args:
            content (str): The content to search for similar concepts.
            retention (int): The number of similar events to retrieve.
            
        Returns:
            A list of (score, node) tuples sorted by score.
        """
        if retention is None:
            retention = config.retention
            
        # Configure weights
        relevance_weight = config.relevance_weight
        importance_weight = config.importance_weight
        recency_weight = config.recency_weight
        
        # Get embedding for the query content
        query_embedding = get_embedding(content)
        
        # Search for similar nodes in the vectorstore
        if self.vs_index.ntotal == 0:
            return []  # Empty index
            
        distances, indices = self.vs_index.search(np.array([query_embedding]), min(self.vs_index.ntotal, retention * 2))
        # Note: this search may return many expired nodes; hence we first find #retention * 2 many, then filter #retention out
        
        # Convert distances (L2) to similarity scores (higher is better)
        max_distance = np.max(distances) if distances.size > 0 else 1.0
        if max_distance == 0:
            max_distance = 1.0  # Avoid division by zero
            
        # Calculate scores for each similar node
        scored_concept_nodes = []
        now = self.curr_time
        
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx >= len(self.vs_id_to_concept_id):
                continue  # Skip if index is out of bounds
                
            concept_id = self.vs_id_to_concept_id[idx]
            concept_node = self.id_to_concept_node[concept_id]
            
            # Skip expired nodes
            if concept_node.expiration and concept_node.expiration < now:
                continue
            
            # Normalize distance to similarity score (1 - normalized_distance)
            """
            #====Alternative method to compute similarity score====
            similarity_score = np.dot(query_embedding, concept_node.embedding) / np.linalg.norm(query_embedding) / np.linalg.norm(concept_node.embedding)
            if similarity_score < 0:
                similarity_score = 0.0 
            """
            similarity_score = 1.0 - (distance / max_distance)
            
            # Importance score is already normalized between 0 and 1
            importance_score = concept_node.importance
            
            # Calculate recency score (newer is better)
            age = now - concept_node.created
            recency_score = config.recency_decay ** (age.total_seconds() /  3600 / 24)  # max(0, 1 - (age / max_age))
            
            # Calculate final score
            score = (
                relevance_weight * similarity_score +
                importance_weight * importance_score +
                recency_weight * recency_score
            )
            
            scored_concept_nodes.append((score, concept_node))
        
        # Sort by score (highest first) and limit to retention
        scored_concept_nodes.sort(key=lambda x: x[0], reverse=True)
        return scored_concept_nodes[:retention]
    
    
    def retrieve_by_spatial_temporal_coincidence(self, maze, spatial_scope, time_scope, retention=None):
        """ 
        Retrieve concepts from long term memory based on spatial-temporal attributes.
        
        Overlap Coefficient (a.k.a. Szymkiewicz–Simpson coefficient) is used for calculating the overlap between two sets.
        We use Overlap Coefficient to compute spatial and temporal relevance.
        
        Spatial matching: 
                                             			              |spatial_coverage(A) ⋂ spatial_coverage(B)|
          spatial_overlap_coefficient between concept A and B  =   -----------------------------------------------------
                                                                      min(|spatial_coverage(A)|, |spatial_coverage(B)|)
        Temporal matching: 
                                             			              |time_scope(A) ⋂ time_scope(B)|
          temporal_overlap_coefficient between concept A and B   =  -----------------------------------------------------
                                           			                   min(|time_scope(A)|,  |time_scope(B)|)
        
        The calculation of spatial_temporal_matching_score:
            spatial_temporal_matching_score = spatial_overlap_coefficient * temporal_overlap_coefficient
        
        Filter events that are spatially and temporally relevant to the given spatial_scope, time_scope, and days.
        score = content_relevance_weight * content_similarity + spatial_temporal_relevance_weight * spatial_temporal_overlap_score + importance_weight * importance_score + recency_weight * recency_score 
        
        Note: 
        1) spatial_scope is converted into spatial_coverage by maze.get_coverage() to get the set needed to compute overlap.
        2) retrieve only concept nodes that indeed have spatial and temporal attributes.
        3) retrieve only active concepts (those with expiration date in the future)

        
        Args:
            maze: The maze object containing spatial_coverage information.
            spatial_scope (str): The spatial_scope of the spatial-temporal attributes.
            time_scope (list[time]): The time scope of the spatial-temporal attributes.
            retention (int): The number of latest events to retrieve.
        
        Returns:
            A list of (score, node) tuples sorted by score.
        """
        if retention is None:
            retention = config.retention
            
        # Configure weights
        relevance_weight = config.relevance_weight
        importance_weight = config.importance_weight
        recency_weight = config.recency_weight
        
        # Generate query spatial_coverage if needed
        query_spatial_coverage = maze.get_coverage(spatial_scope)
        
        # Find all nodes with spatial and temporal attributes
        scored_concept_nodes = []
        now = self.curr_time
        
        for concept_id, concept_node in self.id_to_concept_node.items():
            # Skip expired nodes
            if concept_node.expiration and concept_node.expiration < now:
                continue
                
            # Skip nodes without spatial or temporal attributes
            if concept_node.spatial_scope is None or concept_node.time_scope is None:
                continue
                
            # Get node spatial_coverage
            node_spatial_coverage = maze.get_coverage(concept_node.spatial_scope)
            # Concept node should have spatial_coverage attributes generated using maze.get_coverage() before inserting into long term memory!
            
            # Calculate spatial overlap coefficient
            if not query_spatial_coverage or not node_spatial_coverage:
                spatial_overlap_coefficient = 0.0
            else:
                intersection = set(query_spatial_coverage).intersection(set(node_spatial_coverage))
                min_size = min(len(query_spatial_coverage), len(node_spatial_coverage))
                if min_size == 0:
                    spatial_overlap_coefficient = 0.0
                else:
                    spatial_overlap_coefficient = len(intersection) / min_size
            
            # Calculate temporal overlap coefficient
            if not time_scope or not concept_node.time_scope:
                temporal_overlap_coefficient = 0.0
            else:
                # Convert time objects to minutes for easier comparison
                query_start_minutes = time_scope[0].hour * 60 + time_scope[0].minute
                query_end_minutes = time_scope[1].hour * 60 + time_scope[1].minute
                
                node_start_minutes = concept_node.time_scope[0].hour * 60 + concept_node.time_scope[0].minute
                node_end_minutes = concept_node.time_scope[1].hour * 60 + concept_node.time_scope[1].minute
                
                # Calculate intersection of time intervals
                intersection_start = max(query_start_minutes, node_start_minutes)
                intersection_end = min(query_end_minutes, node_end_minutes)
                
                if intersection_start <= intersection_end:
                    intersection_duration = intersection_end - intersection_start
                    query_duration = query_end_minutes - query_start_minutes
                    node_duration = node_end_minutes - node_start_minutes
                    min_duration = min(query_duration, node_duration)
                    
                    if min_duration > 0:
                        temporal_overlap_coefficient = intersection_duration / min_duration
                    else:
                        temporal_overlap_coefficient = 0.0
                else:
                    # No temporal overlap
                    temporal_overlap_coefficient = 0.0
            
            # Calculate spatial-temporal matching score
            spatial_temporal_matching_score = spatial_overlap_coefficient * temporal_overlap_coefficient
            
            # Skip nodes with no spatial-temporal relevance
            if spatial_temporal_matching_score == 0.0:
                continue
                
            # Importance score is already normalized between 0 and 1
            importance_score = concept_node.importance
            
            # Calculate recency score (newer is better)
            age = now - concept_node.created
            recency_score = config.recency_decay **(age.total_seconds() /  3600 / 24)  #exponential decay; alternative: max(0, 1 - (age / max_age))
            
            # Calculate final score
            score = (
                relevance_weight * spatial_temporal_matching_score +
                importance_weight * importance_score +
                recency_weight * recency_score
            )
            
            scored_concept_nodes.append((score, concept_node))
        
        # Sort by score (highest first) and limit to retention
        scored_concept_nodes.sort(key=lambda x: x[0], reverse=True)
        return scored_concept_nodes[:retention]
    
    
    def retrieve_relevant_concept_nodes(self, concept_node, maze, retention=None):
        """ 
        Retrieve relevant nodes from long term memory based on the given node.
        invoke retrieve_by_keywords, retrieve_by_similarity, and retrieve_by_spatial_temporal_coincidence, 
        and then combine the results into one list and sort them by score;
        return the most relevant #retention nodes.
        Note:
        1) avoid repetition. 
        2) retrieve only active concepts (those with expiration date in the future)
        
        Args:
            concept_node (ConceptNode): The concept node for which you want to retrieve relevant concepts.
            retention (int): The number of relevant events to retrieve.
        
        Returns:
            A list of (score, node) tuples sorted by score.
        """
        if retention is None:
            retention = config.retention
        
        """
        #=====Alternative method for retrieving relevant concept node====
        keyword_results = self.retrieve_by_keywords(concept_node.keywords, retention=retention)
        similarity_results = self.retrieve_by_similarity(concept_node.content, retention=retention)
        spatial_temporal_results = []
        if concept_node.spatial_coverage is not None and concept_node.spatial_coverage != [] and concept_node.time_scope is not None:
            # For simplicity in this implementation, we'll just pass an empty spatial_coverage
            # In a real implementation, you would need to pass the actual maze
            spatial_temporal_results = self.retrieve_by_spatial_temporal_coincidence(concept_node.spatial_coverage, concept_node.time_scope, retention=retention)
        all_results = []
        all_nodes = []
        for score, concept_node in keyword_results:
            if concept_node not in all_nodes:
                all_results.append((score, concept_node))
                all_nodes.append(concept_node)
        for score, concept_node in similarity_results:
            if concept_node not in all_nodes:
                all_results.append((score, concept_node))
                all_nodes.append(concept_node)
        for score, concept_node in spatial_temporal_results:
            if concept_node not in all_nodes:
                all_results.append((score, concept_node))
                all_nodes.append(concept_node)
        return all_results
        """
        
        # Alternative method for retrieving relevant concept node
        # Get results from different retrieval methods
        keyword_results = self.retrieve_by_keywords(concept_node.keywords, retention=retention)
        similarity_results = self.retrieve_by_similarity(concept_node.content, retention=retention)
        # Only perform spatial-temporal retrieval if the concept node has spatial and temporal attributes
        spatial_temporal_results = []
        if concept_node.spatial_scope is not None and concept_node.time_scope is not None:
            # For simplicity in this implementation, we'll just pass an empty spatial_coverage
            # In a real implementation, you would need to pass the actual maze
            spatial_temporal_results = self.retrieve_by_spatial_temporal_coincidence(maze, concept_node.spatial_scope, concept_node.time_scope, retention=retention)
        
        # Combine results and eliminate duplicates
        all_results = {}  # Map concept_id -> (score, node)
        
        # Weight factors for different retrieval methods
        keyword_weight = config.keyword_weight
        similarity_weight = config.similarity_weight
        spatial_temporal_weight = config.spatial_temporal_weight
        
        # Combine with weights
        for score, retrieved_node in keyword_results:
            all_results[retrieved_node.id] = (score * keyword_weight, retrieved_node)
            
        for score, retrieved_node in similarity_results:
            if retrieved_node.id in all_results:
                # Take the max score if already in results
                existing_score = all_results[retrieved_node.id][0]
                all_results[retrieved_node.id] = (max(existing_score, score * similarity_weight), retrieved_node)
            else:
                all_results[retrieved_node.id] = (score * similarity_weight, retrieved_node)
                
        for score, retrieved_node in spatial_temporal_results:
            if retrieved_node.id in all_results:
                # Take the max score if already in results
                existing_score = all_results[retrieved_node.id][0]
                all_results[retrieved_node.id] = (max(existing_score, score * spatial_temporal_weight), retrieved_node)
            else:
                all_results[retrieved_node.id] = (score * spatial_temporal_weight, retrieved_node)
        
        # Exclude the original node
        if concept_node.id in all_results:
            del all_results[concept_node.id]
            
        # Convert back to list and sort by score
        combined_results = list(all_results.values())
        combined_results.sort(key=lambda x: x[0], reverse=True)
        
        # Return up to retention results
        return combined_results[:retention]
    
    
    def retrieve(self, perceived, maze):
        """ 
        Retrieve concepts related to perceived.
        
        Args:
            perceived: a list of ConceptNode object
        """
        # invoke retrieve_relevant nodes
        ans = set()  # to avoid repetition
        for concept_node in perceived:
            tmp_retrieved = self.retrieve_relevant_concept_nodes(concept_node, maze)
            tmp_retrieved = [x[1] for x in tmp_retrieved]  # extract concept nodes
            # remove the current concept node used to retrieve
            if concept_node in tmp_retrieved:
                tmp_retrieved.remove(concept_node)  
            # refresh retrieved concept nodes expiration
            self.refresh_concept_nodes(tmp_retrieved)
            # add to the retrieved concept nodes
            ans.update(tmp_retrieved)
        
        # also include #retention many latest events and #retention many latest chats to avoid immediate forgetting
        # do not refresh those nodes expiration
        latest_concepts = self.seq_concept_ids[- config.retention:]
        latest_concepts = [self.id_to_concept_node[id] for id in latest_concepts if self.id_to_concept_node[id].expiration >= self.curr_time]
        ans.update(latest_concepts)
        
        # remove perceived concept nodes themselves
        for concept_node in perceived:
            ans.discard(concept_node)
        ans = list(ans)
        
        # sort by created time (ascending order)
        ans = sorted(ans, key=lambda x: x.created)
        return ans
    
    def get_summarized_latest_concept_nodes(self, retention=None):
        """ 
        Return a list of recent(#retention many) memory contents;
        used for checking repetition.
        """
        if retention == None:
            retention = config.retention

        return self.concept_contents[-retention:]
    
    
    def refresh_concept_nodes(self, concept_nodes):
        """ 
        Nodes's last_accessed time will be updated to self.curr_time; expiration time will be extended by one day;
        
        Args:
            nodes (list[ConceptNode]): A list of nodes to refresh.
        
        Returns:
            None
        """
        for concept_node in concept_nodes:
            if concept_node.id in self.id_to_concept_node:
                # Update last_accessed time
                concept_node.last_accessed = self.curr_time
                
                # Extend expiration time by some time depending on the type and importance of the concept.
                # here we just extend by lifespan
                expiration_config = config.EXPIRATION_CONFIG.get(concept_node.type, config.EXPIRATION_CONFIG["event"])
                min_hours = expiration_config["min_hours"]
                max_hours = expiration_config["max_hours"]
                power = expiration_config["power"]
                lifespan_hours = min_hours + (max_hours - min_hours) * (concept_node.importance ** power)
                # we add a max_extension to avoid the same kind of memory keep generated and never removed, thus clog the memory
                max_extension = timedelta(hours= config.max_extension_times * lifespan_hours)
                concept_node.expiration = min(self.curr_time + timedelta(hours=lifespan_hours), concept_node.created + max_extension)                    
                
                # Update node in memory
                self.id_to_concept_node[concept_node.id] = concept_node

    
    
if __name__ == "__main__":
    """
    Test function to demonstrate the usage of the LongTermMemory class.
    This will:
    1. Create a new LongTermMemory instance
    2. Create and add several concept nodes of different types
    3. Test different retrieval methods
    4. Demonstrate refreshing nodes
    5. Save and load memory
    6. Clean up expired nodes
    """
    print("Testing LongTermMemory")
    from gatsim.map.maze import Maze
    maze = Maze("the town")
    
    # Create a new LongTermMemory instance
    persona_folder = "gatsim/storage/base_the_town/personas/Isabella Rodriguez"
    os.makedirs(persona_folder, exist_ok=True)
    lt_mem = LongTermMemory(persona_folder)
    
    print("\n1. Adding nodes to memory")
    
    # Create and add an event node
    event_node = ConceptNode(
        type="event",
        created=lt_mem.curr_time - timedelta(days=1),
        content="St_3_link_2 was severely congested around 8 AM on Monday.",
        keywords=["St_3_link_2", "congestion", "morning", "traffic"],
        spatial_scope="St_3_link_2",
        time_scope=[time(8, 0), time(9, 0)],
        importance=0.8
    )
    lt_mem.add_concept_node(event_node)
    print(f"Added event node: {event_node}")
    
    # Create and add a thought node
    thought_node = ConceptNode(
        type="thought",
        created=lt_mem.curr_time - timedelta(hours=12),
        content="I should consider alternative routes to avoid the morning congestion on St_3.",
        keywords=["St_3", "congestion", "morning", "alternative routes"],
        spatial_scope="St_3",
        time_scope=[time(8, 0), time(9, 0)],
        importance=0.7
    )
    lt_mem.add_concept_node(thought_node)
    print(f"Added thought node: {thought_node}")
    
    # Create and add a chat node
    chat_node = ConceptNode(
        type="chat",
        created=lt_mem.curr_time - timedelta(hours=6),
        content="Talked with Bob about traffic conditions on Main Street.",
        keywords=["Bob", "traffic", "Main Street"],
        spatial_scope="St_2",
        time_scope=[time(12, 0), time(12, 30)],
        importance=0.6
    )
    lt_mem.add_concept_node(chat_node)
    print(f"Added chat node: {chat_node}")
    
    # Create and add another event node without spatial-temporal info
    general_event = ConceptNode(
        type="event",
        created=lt_mem.curr_time - timedelta(hours=3),
        content="Finished reading 'Traffic Patterns in Urban Areas' article.",
        keywords=["reading", "article", "traffic patterns", "urban"],
        spatial_scope=None,
        time_scope=None,
        importance=0.5
    )
    lt_mem.add_concept_node(general_event)
    print(f"Added general event node: {general_event}")
    
    print("\n2. Testing keyword-based retrieval")
    keyword_results = lt_mem.retrieve_by_keywords(["congestion", "morning"], retention=3)
    print(f"Found {len(keyword_results)} nodes matching keywords 'congestion', 'morning':")
    for i, (score, node) in enumerate(keyword_results, 1):
        print(f"  {i}. Score: {score:.2f}, Node: {node}")
    
    print("\n3. Testing similarity-based retrieval")
    query = "Traffic congestion in the morning"
    similarity_results = lt_mem.retrieve_by_similarity(query, retention=3)
    print(f"Found {len(similarity_results)} nodes similar to query '{query}':")
    for i, (score, node) in enumerate(similarity_results, 1):
        print(f"  {i}. Score: {score:.2f}, Node: {node}")
    
    print("\n4. Testing relevant nodes retrieval")
    query_node = ConceptNode(
        type="thought",
        created=lt_mem.curr_time,
        content="I'm wondering about the traffic situation on St_3 in the morning.",
        keywords=["St_3", "traffic", "morning"],
        spatial_scope=None,
        time_scope=None,
        importance=0.5
    )
    relevant_results = lt_mem.retrieve_relevant_concept_nodes(query_node, maze, retention=3)
    print(f"Found {len(relevant_results)} nodes relevant to query node:")
    for i, (score, node) in enumerate(relevant_results, 1):
        print(f"  {i}. Score: {score:.2f}, Node: {node}")
    
    print("\n5. Testing refreshing nodes")
    nodes_to_refresh = [lt_mem.id_to_concept_node[concept_id] for concept_id in lt_mem.seq_concept_ids [:2]]
    print(f"Before refresh - Expiration times:")
    for node in nodes_to_refresh:
        print(f"  Node {node.id}: {node.expiration}")
    
    lt_mem.refresh_concept_nodes(nodes_to_refresh)
    
    print(f"After refresh - Expiration times:")
    for node in nodes_to_refresh:
        print(f"  Node {node.id}: {node.expiration}")
    
    print("\n6. Testing saving and loading memory")
    lt_mem.save()
    print(f"Saved memory to {persona_folder}")
    
    # Create a new memory instance and load
    new_lt_mem = LongTermMemory(persona_folder)
    new_lt_mem.load()
    print(f"Loaded memory from {persona_folder}")
    print(f"Number of nodes: {len(new_lt_mem.id_to_concept_node)}")
    
    print("\n7. Testing expired nodes cleanup")
    print(f"Before cleanup: {len(lt_mem.id_to_concept_node)} nodes")
    
    # Artificially expire a node for testing
    first_concept_id = lt_mem.seq_concept_ids [0]
    lt_mem.id_to_concept_node[first_concept_id].expiration = lt_mem.curr_time - timedelta(hours=1)
    print(f"Set node {first_concept_id} to expire at {lt_mem.id_to_concept_node[first_concept_id].expiration}")
    
    lt_mem.clean_up_memory()
    print(f"After cleanup: {len(lt_mem.id_to_concept_node)} nodes")
    
    print("\nTest completed successfully!")