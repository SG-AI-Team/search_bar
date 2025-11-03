from numpy import array

def hybrid_retrieve(vdb, query, k, rank_weight=0.3, sim_weight=0.7, filter=None, where_document=None):
    try:
        search_kwargs = {"k": k}
        if filter:
            search_kwargs["filter"] = filter
        if where_document:
            search_kwargs["where_document"] = where_document
            
        docs_with_scores = vdb.similarity_search_with_score(query, **search_kwargs)
    except Exception as e:
        print(f"Error in similarity_search_with_score: {e}")
        return []
    
    if not docs_with_scores:
        return []
    
    try:
        docs = []
        for doc, distance in docs_with_scores:
            try:
                doc.metadata["similarity_score"] = 1 - distance
                docs.append(doc)
            except Exception as e:
                print(f"Error processing document similarity score: {e}")
                continue
                
        if not docs:
            return []
            
        try:
            similarities = array([d.metadata.get("similarity_score", 0.0) for d in docs])
            ranks = array([d.metadata.get("rank", 0.0) for d in docs])
        except Exception as e:
            print(f"Error creating arrays: {e}")
            return docs  # Return docs without hybrid scoring
        
        try:
            ranks_norm = ranks / ranks.max() if ranks.max() > 0 else ranks
            hybrid_scores = sim_weight * similarities + rank_weight * ranks_norm
        except Exception as e:
            print(f"Error calculating hybrid scores: {e}")
            return docs  # Return docs without hybrid scoring
        
        try:
            for d, s in zip(docs, hybrid_scores):
                d.metadata["hybrid_score"] = float(s)
        except Exception as e:
            print(f"Error assigning hybrid scores: {e}")
        
        try:
            # Separate ranked and unranked schools
            ranked_schools = [d for d in docs if d.metadata.get("rank", 0) > 0]
            unranked_schools = [d for d in docs if d.metadata.get("rank", 0) == 0]
            
            # Sort ranked schools by rank ascending (lower rank number = better)
            ranked_schools.sort(key=lambda d: d.metadata.get("rank", float('inf')))
            
            # Sort unranked schools by hybrid score descending
            unranked_schools.sort(key=lambda d: d.metadata.get("hybrid_score", 0), reverse=True)
            
            # Return ranked schools first, then unranked schools
            return ranked_schools + unranked_schools
        except Exception as e:
            print(f"Error sorting schools: {e}")
            return docs  # Return unsorted docs
            
    except Exception as e:
        print(f"Error in hybrid_retrieve processing: {e}")
        return []