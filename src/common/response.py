from typing import Any, Optional, Dict
from fastapi import HTTPException, status

class ResponseHandler:
    @staticmethod
    def not_found_error(entity: str, id: Any) -> None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity} with id {id} not found"
        )
    
    @staticmethod
    def get_single_success(name: str, id: Any, data: Any) -> Dict[str, Any]:
        return {
            "message": f"Successfully retrieved {name}",
            "data": data
        }
    
    @staticmethod
    def create_success(name: str, id: Any, data: Any) -> Dict[str, Any]:
        return {
            "message": f"Successfully created {name}",
            "data": data
        }
    
    @staticmethod
    def update_success(name: str, id: Any, data: Any) -> Dict[str, Any]:
        return {
            "message": f"Successfully updated {name}",
            "data": data
        }
    
    @staticmethod
    def delete_success(name: str, id: Any, data: Any) -> Dict[str, Any]:
        return {
            "message": f"Successfully deleted {name}",
            "data": data
        }