import json
import logging
from typing import Optional, Tuple, Any

from core.models import ConflictResolutionResult, KnowledgeGraph
from core.config import ModelConfig
from core.interfaces import LLMClient

logger = logging.getLogger(__name__)

class MockOpenAIClient(LLMClient):
    """Mock client for testing that implements the LLMClient interface."""

    def __init__(self, think_tags: Tuple[str, str], reasoning_model_config: ModelConfig, entity_extraction_model_config: ModelConfig, conflict_resolution_model_config: ModelConfig):
        """Initializes the MockOpenAIClient with configurations."""
        self.think_tags = think_tags
        self.reasoning_model_config = reasoning_model_config
        self.entity_extraction_model_config = entity_extraction_model_config
        self.conflict_resolution_model_config = conflict_resolution_model_config

    def conflict_resolution(self, prompt: str) -> Optional[ConflictResolutionResult]:
        """Mock implementation of conflict resolution."""
        logger.info(f"Mock conflict resolution for prompt: {prompt}")
        
        # Return a mock conflict resolution result
        result = {
            "reasoning": "This is a mock reasoning for conflict resolution.",
            "action": "keep_existing",
            "new_name": None,
            "new_description": None
        }
        
        return ConflictResolutionResult(**result)

    def generate_reasoning_trace(self, prompt: str) -> Optional[str]:
        """Mock implementation of reasoning trace generation."""
        logger.info(f"Mock reasoning trace for prompt: {prompt}")
        
        # Generate a mock reasoning trace based on the prompt
        if "Ancient Egypt" in prompt or "pyramids" in prompt:
            reasoning = f"{self.think_tags[0]}\nAncient Egypt was one of the world's first great civilizations, flourishing along the Nile River from about 3100 BCE to 30 BCE. The pyramids were massive monuments built as tombs for pharaohs. The Great Pyramid of Giza, built for Pharaoh Khufu around 2560 BCE, is the largest and most famous. Pyramid construction involved thousands of workers, including skilled craftsmen and laborers. They used simple tools like copper chisels, wooden mallets, and ropes, yet achieved remarkable precision. The pyramids were part of elaborate funerary complexes designed to help the pharaoh's journey to the afterlife. Contrary to popular belief, archaeological evidence suggests that the pyramid workers were not slaves but paid laborers, often farmers who worked during the Nile's annual flood when they couldn't farm. The construction techniques remain a subject of debate, with theories including ramps, levers, and pulley systems.\n{self.think_tags[1]}"
        elif "Afterlife" in prompt:
            reasoning = f"{self.think_tags[0]}\nThe ancient Egyptian concept of the afterlife was complex and central to their religion. They believed in a journey after death where the soul (Ka and Ba) would travel through the underworld (Duat) to reach the Hall of Judgment. There, the god Anubis would weigh the deceased's heart against the feather of Ma'at (truth and justice). If the heart was lighter, they would join Osiris in the Field of Reeds, a paradise resembling Egypt. If heavier, the heart would be devoured by Ammit, resulting in a second death. To prepare for this journey, Egyptians developed elaborate burial practices including mummification to preserve the body, funerary texts like the Book of the Dead to guide the soul, and tomb goods to assist in the afterlife. The pharaoh was believed to become one with the sun god Ra, traveling across the sky daily.\n{self.think_tags[1]}"
        elif "Nile River" in prompt:
            reasoning = f"{self.think_tags[0]}\nThe Nile River was the lifeblood of ancient Egyptian civilization, flowing north from the highlands of East Africa to the Mediterranean Sea. Its annual flooding cycle deposited rich silt along its banks, creating fertile farmland in an otherwise desert region. This predictable inundation, occurring between June and September, allowed for sophisticated agricultural practices and food surpluses that supported Egypt's complex society. The Nile also served as the primary transportation route, facilitating trade, communication, and the movement of building materials for monuments. Egyptians divided their land into Upper Egypt (the southern, upstream region) and Lower Egypt (the northern delta region). The river influenced Egyptian religion, with the god Hapi personifying the annual flood and the Nile itself considered divine. Nilometers were constructed to measure the height of the annual flood, helping predict harvest yields and tax assessments.\n{self.think_tags[1]}"
        elif "Greek philosophers" in prompt or "Socrates" in prompt or "Plato" in prompt or "Aristotle" in prompt:
            reasoning = f"{self.think_tags[0]}\nAristotle (384-322 BCE) was a Greek philosopher and polymath who made significant contributions to numerous fields including logic, metaphysics, ethics, politics, biology, and more. As a student of Plato and tutor to Alexander the Great, his influence spanned both philosophical thought and practical governance. Aristotle founded the Peripatetic School at the Lyceum in Athens, where he developed his distinctive approach to knowledge based on empirical observation and logical analysis. His major works include Nicomachean Ethics, which explores virtue ethics and the concept of eudaimonia (happiness or human flourishing); Metaphysics, which examines the nature of reality and introduces concepts like substance, form, and matter; and Politics, which analyzes different forms of government and proposes the ideal state. Aristotle's scientific contributions included systematic classification of plants and animals, and his theory of the four causes (material, formal, efficient, and final) provided a framework for understanding natural phenomena. His logical works, collectively known as the Organon, established the foundation for formal logic that remained dominant until the 19th century.\n{self.think_tags[1]}"
        elif "Sweden" in prompt:
            reasoning = f"{self.think_tags[0]}\nSweden maintained neutrality during World War II, though it did have economic ties with Nazi Germany. Sweden allowed German troops to travel through its territory to Norway and Finland. Sweden also provided iron ore to Germany, which was crucial for the German war effort. However, Sweden also helped save thousands of Jews from Nazi persecution, particularly from Denmark and Norway. Sweden's policy was primarily focused on maintaining its independence and avoiding being drawn into the conflict.\n{self.think_tags[1]}"
        else:
            reasoning = f"{self.think_tags[0]}\nThis is a mock reasoning trace for the prompt: {prompt}. It would contain detailed analysis and exploration of the topic.\n{self.think_tags[1]}"
        
        print(reasoning)
        return reasoning

    def extract_knowledge_graph(self, prompt: str) -> Optional[KnowledgeGraph]:
        """Mock implementation of knowledge graph extraction."""
        logger.info(f"Mock knowledge graph extraction for prompt: {prompt}")
        print(f"DEBUG - Extract KG prompt: {prompt[:100]}...")
        
        # Extract the content from the prompt
        content_start = prompt.find("<content>")
        content_end = prompt.find("</content>")
        
        if content_start != -1 and content_end != -1:
            content = prompt[content_start + 9:content_end].strip()
            print(f"DEBUG - Content: {content[:100]}...")
        else:
            content = prompt
            
        # Generate a mock knowledge graph based on the content
        if "Ancient Egypt" in content or "pyramids" in content:
            print("DEBUG - Using Ancient Egypt KG data")
        elif "Afterlife" in content and "Ka and Ba" in content:
            print("DEBUG - Using Afterlife KG data")
        elif "Nile River" in content and "annual flooding" in content:
            print("DEBUG - Using Nile River KG data")
        elif "Greek philosophers" in content or "Socrates" in content or "Plato" in content or "Aristotle" in content:
            print("DEBUG - Using Greek Philosophers KG data")
            
        # Generate a mock knowledge graph based on the content
        if "Greek philosophers" in content or "Socrates" in content or "Plato" in content or "Aristotle" in content:
            kg_data = {
                "entities": [
                    {
                        "name": "Socrates",
                        "description": "Classical Greek philosopher credited as the founder of Western philosophy",
                        "category": ["Philosopher", "Historical Figure"]
                    },
                    {
                        "name": "Plato",
                        "description": "Ancient Greek philosopher, student of Socrates and teacher of Aristotle",
                        "category": ["Philosopher", "Writer"]
                    },
                    {
                        "name": "Aristotle",
                        "description": "Greek philosopher and polymath who founded the Peripatetic school of philosophy",
                        "category": ["Philosopher", "Scientist"]
                    },
                    {
                        "name": "Academy",
                        "description": "School founded by Plato in Athens, one of the earliest known organized schools",
                        "category": ["Institution", "School"]
                    },
                    {
                        "name": "Lyceum",
                        "description": "School founded by Aristotle in Athens, focused on collaborative research",
                        "category": ["Institution", "Research Center"]
                    },
                    {
                        "name": "Theory of Forms",
                        "description": "Plato's philosophical theory that abstract forms represent the true reality",
                        "category": ["Philosophical Theory", "Metaphysics"]
                    }
                ],
                "relationships": [
                    {
                        "source_entity_name": "Socrates",
                        "target_entity_name": "Plato",
                        "relation_type": "taught",
                        "attributes": {"method": "dialectic questioning"}
                    },
                    {
                        "source_entity_name": "Plato",
                        "target_entity_name": "Aristotle",
                        "relation_type": "taught",
                        "attributes": {"duration": "20 years"}
                    },
                    {
                        "source_entity_name": "Plato",
                        "target_entity_name": "Academy",
                        "relation_type": "founded",
                        "attributes": {"year": "387 BCE"}
                    },
                    {
                        "source_entity_name": "Aristotle",
                        "target_entity_name": "Lyceum",
                        "relation_type": "founded",
                        "attributes": {"year": "335 BCE"}
                    },
                    {
                        "source_entity_name": "Plato",
                        "target_entity_name": "Theory of Forms",
                        "relation_type": "developed",
                        "attributes": {"central_work": "Republic"}
                    }
                ]
            }
        elif "Ancient Egypt" in content or "pyramids" in content:
            kg_data = {
                "entities": [
                    {
                        "name": "Ancient Egypt",
                        "description": "One of the world's first great civilizations, flourishing along the Nile River from about 3100 BCE to 30 BCE",
                        "category": ["Civilization", "Ancient Culture"]
                    },
                    {
                        "name": "Great Pyramid of Giza",
                        "description": "The largest and most famous pyramid, built for Pharaoh Khufu around 2560 BCE",
                        "category": ["Monument", "Wonder of the Ancient World"]
                    },
                    {
                        "name": "Pharaoh Khufu",
                        "description": "The second pharaoh of the Fourth Dynasty of Egypt's Old Kingdom, who commissioned the Great Pyramid",
                        "category": ["Ruler", "Historical Figure"]
                    },
                    {
                        "name": "Nile River",
                        "description": "The major river in northeastern Africa that enabled Egyptian civilization to flourish",
                        "category": ["Geographical Feature", "Water Source"]
                    },
                    {
                        "name": "Pyramid Workers",
                        "description": "The laborers who built the pyramids, believed to be paid workers rather than slaves",
                        "category": ["Social Group", "Labor Force"]
                    },
                    {
                        "name": "Afterlife",
                        "description": "The concept of life after death in ancient Egyptian religion",
                        "category": ["Religious Concept", "Spiritual Belief"]
                    }
                ],
                "relationships": [
                    {
                        "source_entity_name": "Ancient Egypt",
                        "target_entity_name": "Nile River",
                        "relation_type": "developed_along",
                        "attributes": {"period": "3100 BCE - 30 BCE"}
                    },
                    {
                        "source_entity_name": "Pharaoh Khufu",
                        "target_entity_name": "Great Pyramid of Giza",
                        "relation_type": "commissioned",
                        "attributes": {"date": "circa 2560 BCE"}
                    },
                    {
                        "source_entity_name": "Pyramid Workers",
                        "target_entity_name": "Great Pyramid of Giza",
                        "relation_type": "constructed",
                        "attributes": {"tools_used": "copper chisels, wooden mallets, ropes"}
                    },
                    {
                        "source_entity_name": "Great Pyramid of Giza",
                        "target_entity_name": "Afterlife",
                        "relation_type": "facilitated_journey_to",
                        "attributes": {"for": "Pharaoh Khufu"}
                    },
                    {
                        "source_entity_name": "Ancient Egypt",
                        "target_entity_name": "Great Pyramid of Giza",
                        "relation_type": "created",
                        "attributes": {"purpose": "royal tomb"}
                    }
                ]
            }
        elif "Sweden" in prompt:
            kg_data = {
                "entities": [
                    {
                        "name": "Sweden",
                        "description": "A Nordic country that maintained neutrality during World War II",
                        "category": ["Country", "European Nation"]
                    },
                    {
                        "name": "Nazi Germany",
                        "description": "The German state under Adolf Hitler's rule from 1933 to 1945",
                        "category": ["Country", "Axis Power"]
                    },
                    {
                        "name": "Iron Ore",
                        "description": "A key natural resource exported from Sweden to Germany during WWII",
                        "category": ["Natural Resource", "War Material"]
                    },
                    {
                        "name": "Neutrality Policy",
                        "description": "Sweden's official stance during World War II",
                        "category": ["Foreign Policy", "Diplomatic Strategy"]
                    },
                    {
                        "name": "Jewish Refugees",
                        "description": "People fleeing Nazi persecution who found safety in Sweden",
                        "category": ["Refugee Group", "Holocaust Victims"]
                    }
                ],
                "relationships": [
                    {
                        "source_entity_name": "Sweden",
                        "target_entity_name": "Nazi Germany",
                        "relation_type": "traded_with",
                        "attributes": {"primary_export": "Iron ore"}
                    },
                    {
                        "source_entity_name": "Sweden",
                        "target_entity_name": "Neutrality Policy",
                        "relation_type": "adopted",
                        "attributes": {"period": "1939-1945"}
                    },
                    {
                        "source_entity_name": "Sweden",
                        "target_entity_name": "Jewish Refugees",
                        "relation_type": "provided_sanctuary_to",
                        "attributes": {"estimated_number": "thousands"}
                    },
                    {
                        "source_entity_name": "Sweden",
                        "target_entity_name": "Iron Ore",
                        "relation_type": "exported",
                        "attributes": {"recipient": "Nazi Germany"}
                    }
                ]
            }
        elif "Afterlife" in content:
            kg_data = {
                "entities": [
                    {
                        "name": "Ka",
                        "description": "One aspect of the Egyptian soul, representing life force or vital essence",
                        "category": ["Spiritual Concept", "Soul Component"]
                    },
                    {
                        "name": "Ba",
                        "description": "The personality or soul aspect that could leave the body after death",
                        "category": ["Spiritual Concept", "Soul Component"]
                    },
                    {
                        "name": "Duat",
                        "description": "The Egyptian underworld through which the soul journeyed after death",
                        "category": ["Mythological Realm", "Afterlife Location"]
                    },
                    {
                        "name": "Anubis",
                        "description": "The jackal-headed god who oversaw mummification and weighed the heart in judgment",
                        "category": ["Deity", "Funerary God"]
                    },
                    {
                        "name": "Book of the Dead",
                        "description": "Collection of spells and instructions to help navigate the afterlife",
                        "category": ["Religious Text", "Funerary Document"]
                    },
                    {
                        "name": "Osiris",
                        "description": "God of the afterlife who ruled the realm of the dead",
                        "category": ["Deity", "Afterlife Ruler"]
                    }
                ],
                "relationships": [
                    {
                        "source_entity_name": "Afterlife",
                        "target_entity_name": "Duat",
                        "relation_type": "includes_realm",
                        "attributes": {"importance": "primary underworld"}
                    },
                    {
                        "source_entity_name": "Anubis",
                        "target_entity_name": "Afterlife",
                        "relation_type": "judges_souls_in",
                        "attributes": {"method": "weighing of the heart"}
                    },
                    {
                        "source_entity_name": "Book of the Dead",
                        "target_entity_name": "Afterlife",
                        "relation_type": "provides_guidance_for",
                        "attributes": {"purpose": "safe passage"}
                    },
                    {
                        "source_entity_name": "Osiris",
                        "target_entity_name": "Afterlife",
                        "relation_type": "rules_over",
                        "attributes": {"realm": "Field of Reeds"}
                    },
                    {
                        "source_entity_name": "Ka",
                        "target_entity_name": "Afterlife",
                        "relation_type": "journeys_through",
                        "attributes": {"with": "Ba"}
                    }
                ]
            }
        elif "Nile River" in content:
            kg_data = {
                "entities": [
                    {
                        "name": "Annual Flood",
                        "description": "The yearly inundation of the Nile that deposited fertile silt on farmlands",
                        "category": ["Natural Phenomenon", "Agricultural Event"]
                    },
                    {
                        "name": "Upper Egypt",
                        "description": "The southern region of ancient Egypt, upstream along the Nile",
                        "category": ["Geographic Region", "Political Division"]
                    },
                    {
                        "name": "Lower Egypt",
                        "description": "The northern delta region of ancient Egypt",
                        "category": ["Geographic Region", "Political Division"]
                    },
                    {
                        "name": "Hapi",
                        "description": "The god of the annual flooding of the Nile",
                        "category": ["Deity", "Fertility God"]
                    },
                    {
                        "name": "Nilometer",
                        "description": "Structure used to measure the height of the Nile's annual flood",
                        "category": ["Measurement Tool", "Agricultural Technology"]
                    }
                ],
                "relationships": [
                    {
                        "source_entity_name": "Nile River",
                        "target_entity_name": "Annual Flood",
                        "relation_type": "produces",
                        "attributes": {"season": "summer"}
                    },
                    {
                        "source_entity_name": "Nile River",
                        "target_entity_name": "Upper Egypt",
                        "relation_type": "flows_through",
                        "attributes": {"direction": "northward"}
                    },
                    {
                        "source_entity_name": "Nile River",
                        "target_entity_name": "Lower Egypt",
                        "relation_type": "forms_delta_in",
                        "attributes": {"location": "Mediterranean coast"}
                    },
                    {
                        "source_entity_name": "Hapi",
                        "target_entity_name": "Nile River",
                        "relation_type": "personifies",
                        "attributes": {"aspect": "flooding"}
                    },
                    {
                        "source_entity_name": "Nilometer",
                        "target_entity_name": "Annual Flood",
                        "relation_type": "measures",
                        "attributes": {"purpose": "predict harvest"}
                    }
                ]
            }
        else:
            kg_data = {
                "entities": [
                    {
                        "name": "Entity 1",
                        "description": "Description of Entity 1",
                        "category": ["Category A", "Category B"]
                    },
                    {
                        "name": "Entity 2",
                        "description": "Description of Entity 2",
                        "category": ["Category C"]
                    }
                ],
                "relationships": [
                    {
                        "source_entity_name": "Entity 1",
                        "target_entity_name": "Entity 2",
                        "relation_type": "related_to",
                        "attributes": {"attribute1": "value1"}
                    }
                ]
            }
        
        kg_json = json.dumps(kg_data, indent=2)
        print(kg_json)
        return KnowledgeGraph(**kg_data)