from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.getenv("DB_NAME", "devagent")

        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        self.projects = self.db.projects
        self.files = self.db.files

    async def create_project(self, project_data: Dict) -> str:
        """Create a new project"""
        project_data["created_at"] = datetime.utcnow()
        project_data["updated_at"] = datetime.utcnow()
        result = await self.projects.insert_one(project_data)
        return str(result.inserted_id)

    async def get_project(self, project_id: str) -> Optional[Dict]:
        """Get a project by ID"""
        try:
            project = await self.projects.find_one({"_id": ObjectId(project_id)})
            if project:
                project["id"] = str(project["_id"])
                del project["_id"]
            return project
        except:
            return None

    async def get_all_projects(self) -> List[Dict]:
        """Get all projects"""
        cursor = self.projects.find().sort("created_at", -1)
        projects = []
        async for project in cursor:
            project["id"] = str(project["_id"])
            del project["_id"]
            projects.append(project)
        return projects

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        try:
            result = await self.projects.delete_one({"_id": ObjectId(project_id)})
            return result.deleted_count > 0
        except:
            return False

    async def save_file(self, file_data: Dict) -> str:
        """Save or update a file"""
        file_data["updated_at"] = datetime.utcnow()

        # Check if file exists
        existing = await self.files.find_one({
            "project_id": file_data["project_id"],
            "path": file_data["path"]
        })

        if existing:
            # Update existing file
            await self.files.update_one(
                {"_id": existing["_id"]},
                {"$set": file_data}
            )
            return str(existing["_id"])
        else:
            # Create new file
            result = await self.files.insert_one(file_data)
            return str(result.inserted_id)

    async def get_files_by_project(self, project_id: str) -> List[Dict]:
        """Get all files for a project"""
        cursor = self.files.find({"project_id": project_id}).sort("path", 1)
        files = []
        async for file in cursor:
            file["id"] = str(file["_id"])
            del file["_id"]
            files.append(file)
        return files

    async def get_file(self, project_id: str, path: str) -> Optional[Dict]:
        """Get a specific file"""
        file = await self.files.find_one({
            "project_id": project_id,
            "path": path
        })
        if file:
            file["id"] = str(file["_id"])
            del file["_id"]
        return file

    async def delete_file(self, project_id: str, path: str) -> bool:
        """Delete a file"""
        try:
            result = await self.files.delete_one({
                "project_id": project_id,
                "path": path
            })
            return result.deleted_count > 0
        except:
            return False

    async def delete_files_by_project(self, project_id: str) -> int:
        """Delete all files for a project"""
        try:
            result = await self.files.delete_many({"project_id": project_id})
            return result.deleted_count
        except:
            return 0

