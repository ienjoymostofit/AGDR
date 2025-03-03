import logging
from typing import Optional, List, Tuple

from core.interfaces import GraphPopulator, GraphDatabase, ConflictResolver
from core.models import Entity, Relationship, KnowledgeGraph
from services.embed_service import EmbedService

logger = logging.getLogger(__name__)

class GraphPopulationService(GraphPopulator):
    """Service for populating the knowledge graph with entities and relationships."""
    
    def __init__(self, graph_db: GraphDatabase, embed_service: EmbedService, conflict_resolver: ConflictResolver):
        """
        Initialize the graph population service.
        
        Args:
            graph_db: The graph database client
            embed_service: The embedding service for similarity checks
            conflict_resolver: The conflict resolution service
        """
        self.graph_db = graph_db
        self.embed_service = embed_service
        self.conflict_resolver = conflict_resolver
        
    def add_entity(self, entity: Entity) -> Optional[str]:
        """
        Adds an entity to the knowledge graph, handling potential conflicts and generating embeddings.
        """
        logger.info(f"Adding entity: {entity.name}")
        
        # Check for similar entities by name
        similar_entities_by_name = self.embed_service.find_similar_entities_by_entity_name(entity.name)
        similar_entities_by_description = self.embed_service.find_similar_entities_by_description(
            entity.name, entity.description
        )
        
        # Combine similarity results
        similar_entities = []
        if similar_entities_by_name and similar_entities_by_description:
            similar_entities = similar_entities_by_name + similar_entities_by_description
        elif similar_entities_by_name:
            similar_entities = similar_entities_by_name
        elif similar_entities_by_description:
            similar_entities = similar_entities_by_description
            
        # If we found similar entities, check if we need conflict resolution
        entity_id = None
        if similar_entities:
            # Sort by similarity score
            similar_entities.sort(key=lambda x: x[2], reverse=True)
            
            most_similar_entity = similar_entities[0]
            similar_entity_name = most_similar_entity[0]
            similarity_score = most_similar_entity[2]
            
            logger.info(f"Most similar entity: {similar_entity_name}, Similarity Score: {similarity_score}")
            
            # Very high similarity - assume it's the same entity
            if similarity_score >= 0.975 and entity.name != similar_entity_name:
                logger.info(f"Entity '{entity.name}' is very similar to existing entity '{similar_entity_name}' with score {similarity_score}. Using existing entity.")
                entity.name = similar_entity_name
                entity_id = self.graph_db.get_node_by_name(similar_entity_name).id
            
            # Moderate similarity - needs conflict resolution
            elif similarity_score >= 0.85:
                logger.info(f"Entity '{entity.name}' has a similar entity '{similar_entity_name}' with score {similarity_score}. Resolving conflict.")
                existing_entity = self.graph_db.get_node_by_name(similar_entity_name)
                
                # Resolve the conflict
                resolution = self.conflict_resolver.resolve_entity_conflict(existing_entity, entity)
                
                # Apply the resolution
                if resolution.action == "same":
                    logger.info(f"Conflict resolution: entities are the same, using '{existing_entity.name}'")
                    entity.name = existing_entity.name
                    entity_id = existing_entity.id
                elif resolution.action == "merge":
                    new_name = resolution.new_name or existing_entity.name
                    new_description = resolution.new_description or existing_entity.description
                    
                    logger.info(f"Conflict resolution: merging entities into '{new_name}'")
                    
                    # Update the existing entity with the merged information
                    self.graph_db.update_node_name_and_description(
                        existing_entity.name, new_name, new_description
                    )
                    
                    # Update our current entity
                    entity.name = new_name
                    entity.description = new_description
                    entity_id = existing_entity.id
                    
                    # Update the embedding for the merged entity
                    self.embed_service.embed_entity(new_name, new_description)
                # For "distinct", we'll create a new entity below
        
        # If we didn't find a matching entity or the entities are distinct, create a new one
        if not entity_id:
            entity_id = self.graph_db.create_node(entity)
            if entity_id:
                logger.info(f"Created new entity: {entity.name}, ID: {entity_id}")
                # Generate embedding for the new entity
                self.embed_service.embed_entity(entity.name, entity.description)
            else:
                logger.warning(f"Failed to create entity: {entity.name}")
                
        return entity_id
    
    def add_relationship(self, relationship: Relationship) -> bool:
        """
        Adds a relationship to the knowledge graph.
        """
        logger.info(f"Adding relationship: {relationship.source_entity_name} -> {relationship.relation_type} -> {relationship.target_entity_name}")
        
        try:
            self.graph_db.create_relationship(relationship)
            return True
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False
    
    def merge_knowledge_graph(self, knowledge_graph: KnowledgeGraph) -> KnowledgeGraph:
        """
        Merges a knowledge graph into the existing graph.
        
        Processes all entities and relationships, handling potential conflicts.
        """
        logger.info(f"Merging knowledge graph with {len(knowledge_graph.entities)} entities and {len(knowledge_graph.relationships)} relationships")
        
        # Track entity name updates to update relationships later
        name_updates = {}
        
        # First, process all entities
        for entity in knowledge_graph.entities:
            original_name = entity.name
            entity_id = self.add_entity(entity)
            
            # If the name changed during entity addition, track it for relationship updates
            if entity.name != original_name:
                name_updates[original_name] = entity.name
        
        # Update relationship entity names if they changed during entity processing
        for relationship in knowledge_graph.relationships:
            if relationship.source_entity_name in name_updates:
                relationship.source_entity_name = name_updates[relationship.source_entity_name]
            if relationship.target_entity_name in name_updates:
                relationship.target_entity_name = name_updates[relationship.target_entity_name]
            
            # Add the relationship
            self.add_relationship(relationship)
        
        # Return the potentially modified knowledge graph
        return knowledge_graph