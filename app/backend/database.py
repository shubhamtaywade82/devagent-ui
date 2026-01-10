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
        self.instruments = self.db.instruments

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
                # Convert datetime objects to ISO format strings
                if "created_at" in project and project["created_at"]:
                    project["created_at"] = project["created_at"].isoformat()
                if "updated_at" in project and project["updated_at"]:
                    project["updated_at"] = project["updated_at"].isoformat()
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
            # Convert datetime objects to ISO format strings
            if "created_at" in project and project["created_at"]:
                project["created_at"] = project["created_at"].isoformat()
            if "updated_at" in project and project["updated_at"]:
                project["updated_at"] = project["updated_at"].isoformat()
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
            # Convert datetime objects to ISO format strings
            if "updated_at" in file and file["updated_at"]:
                file["updated_at"] = file["updated_at"].isoformat()
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
            # Convert datetime objects to ISO format strings
            if "updated_at" in file and file["updated_at"]:
                file["updated_at"] = file["updated_at"].isoformat()
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

    # Instruments methods
    async def save_instruments(self, instruments: List[Dict], format_type: str = "detailed") -> Dict:
        """Save or update instruments in database"""
        try:
            # Delete existing instruments
            await self.instruments.delete_many({"format": format_type})

            # Insert new instruments with metadata
            now = datetime.utcnow()
            instruments_with_meta = []
            for inst in instruments:
                inst_data = {
                    **inst,
                    "format": format_type,
                    "updated_at": now
                }
                instruments_with_meta.append(inst_data)

            if instruments_with_meta:
                await self.instruments.insert_many(instruments_with_meta)

            # Update metadata
            await self.instruments.update_one(
                {"_id": "metadata"},
                {
                    "$set": {
                        "last_updated": now,
                        "format": format_type,
                        "count": len(instruments),
                        "updated_at": now
                    }
                },
                upsert=True
            )

            return {
                "success": True,
                "count": len(instruments),
                "updated_at": now.isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_instruments(self, format_type: str = "detailed", limit: Optional[int] = None) -> List[Dict]:
        """Get instruments from database"""
        try:
            query = {"format": format_type}
            cursor = self.instruments.find(query)

            if limit:
                cursor = cursor.limit(limit)

            instruments = []
            async for inst in cursor:
                # Remove MongoDB _id and format field
                inst.pop("_id", None)
                inst.pop("format", None)
                inst.pop("updated_at", None)
                instruments.append(inst)

            return instruments
        except Exception as e:
            print(f"Error getting instruments from database: {e}")
            return []

    async def get_instruments_metadata(self) -> Optional[Dict]:
        """Get instruments metadata (last update time, count, etc.)"""
        try:
            metadata = await self.instruments.find_one({"_id": "metadata"})
            if metadata:
                metadata["id"] = str(metadata.get("_id", ""))
                if "_id" in metadata:
                    del metadata["_id"]
                if "last_updated" in metadata and metadata["last_updated"]:
                    metadata["last_updated"] = metadata["last_updated"].isoformat()
                if "updated_at" in metadata and metadata["updated_at"]:
                    metadata["updated_at"] = metadata["updated_at"].isoformat()
            return metadata
        except Exception as e:
            print(f"Error getting instruments metadata: {e}")
            return None

    async def instruments_exist(self, format_type: str = "detailed") -> bool:
        """Check if instruments exist in database"""
        try:
            count = await self.instruments.count_documents({"format": format_type})
            return count > 0
        except:
            return False

