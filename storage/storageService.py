import csv
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class ChatInfo:
    """Data class for chat information"""
    chat_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    date_added: str = ""
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, str]:
        return {
            'chat_id': str(self.chat_id),
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_added': self.date_added,
            'is_active': str(self.is_active)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ChatInfo':
        return cls(
            chat_id=int(data['chat_id']),
            username=data.get('username', ''),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            date_added=data.get('date_added', ''),
            is_active=data.get('is_active', 'True').lower() == 'true'
        )

class StorageService:
    def __init__(self, csv_file_path: str = None):
        """
        Initialize the chat ID storage service
        
        Args:
            csv_file_path: Path to the CSV file. If None, uses default path.
        """
        if csv_file_path is None:
            current_dir = os.path.dirname(__file__)
            self.csv_file_path = os.path.join(current_dir, 'chat_ids.csv')
        else:
            self.csv_file_path = csv_file_path
        
        self._ensure_csv_exists()
    
    def _ensure_csv_exists(self):
        """Ensure the CSV file exists with proper headers"""
        if not os.path.exists(self.csv_file_path):
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as file:
                fieldnames = ['chat_id', 'username', 'first_name', 'last_name', 'date_added', 'is_active']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
    
    def saveChat(self, chat_id: int, username: str = "", first_name: str = "", last_name: str = "") -> bool:
        """
        Save a new chat ID to the CSV file
        
        Args:
            chat_id: Telegram chat ID
            username: Optional username
            first_name: Optional first name
            last_name: Optional last name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if chat_id already exists
            if self.get_chat_info(chat_id):
                print(f"Chat ID {chat_id} already exists")
                return False
            
            chat_info = ChatInfo(
                chat_id=chat_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                date_added=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                is_active=True
            )
            
            fieldnames = ['chat_id', 'username', 'first_name', 'last_name', 'date_added', 'is_active']
            
            with open(self.csv_file_path, 'a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writerow(chat_info.to_dict())
            
            print(f"Chat ID {chat_id} saved successfully")
            return True
            
        except Exception as e:
            print(f"Error saving chat ID: {e}")
            return False
    
    def getAllChatIds(self) -> List[int]:
        """
        Get all chat IDs from the CSV file
        
        Returns:
            List[int]: List of all chat IDs
        """
        try:
            chat_ids = []
            with open(self.csv_file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row.get('is_active', 'True').lower() == 'true':
                        chat_ids.append(int(row['chat_id']))
            return chat_ids
        except FileNotFoundError:
            print(f"CSV file not found: {self.csv_file_path}")
            return []
        except Exception as e:
            print(f"Error reading chat IDs: {e}")
            return []
    
    def get_all_chat_info(self) -> List[ChatInfo]:
        """
        Get all chat information from the CSV file
        
        Returns:
            List[ChatInfo]: List of all chat info objects
        """
        try:
            chat_infos = []
            with open(self.csv_file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    chat_infos.append(ChatInfo.from_dict(row))
            return chat_infos
        except FileNotFoundError:
            print(f"CSV file not found: {self.csv_file_path}")
            return []
        except Exception as e:
            print(f"Error reading chat info: {e}")
            return []
    
    def get_active_chat_ids(self) -> List[int]:
        """
        Get only active chat IDs
        
        Returns:
            List[int]: List of active chat IDs
        """
        all_info = self.get_all_chat_info()
        return [info.chat_id for info in all_info if info.is_active]
    
    def get_chat_info(self, chat_id: int) -> Optional[ChatInfo]:
        """
        Get information for a specific chat ID
        
        Args:
            chat_id: Chat ID to look up
            
        Returns:
            ChatInfo or None: Chat information if found
        """
        all_info = self.get_all_chat_info()
        for info in all_info:
            if info.chat_id == chat_id:
                return info
        return None
    
    def delete_chat_id(self, chat_id: int) -> bool:
        """
        Delete a chat ID from the CSV file
        
        Args:
            chat_id: Chat ID to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            all_info = self.get_all_chat_info()
            original_count = len(all_info)
            
            # Filter out the chat_id to delete
            filtered_info = [info for info in all_info if info.chat_id != chat_id]
            
            if len(filtered_info) < original_count:
                self._write_all_chat_info(filtered_info)
                print(f"Chat ID {chat_id} deleted successfully")
                return True
            else:
                print(f"Chat ID {chat_id} not found")
                return False
                
        except Exception as e:
            print(f"Error deleting chat ID: {e}")
            return False
    
    def deactivate_chat_id(self, chat_id: int) -> bool:
        """
        Mark a chat ID as inactive (soft delete)
        
        Args:
            chat_id: Chat ID to deactivate
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            all_info = self.get_all_chat_info()
            updated = False
            
            for info in all_info:
                if info.chat_id == chat_id:
                    info.is_active = False
                    updated = True
                    break
            
            if updated:
                self._write_all_chat_info(all_info)
                print(f"Chat ID {chat_id} deactivated successfully")
                return True
            else:
                print(f"Chat ID {chat_id} not found")
                return False
                
        except Exception as e:
            print(f"Error deactivating chat ID: {e}")
            return False
    
    def activate_chat_id(self, chat_id: int) -> bool:
        """
        Mark a chat ID as active
        
        Args:
            chat_id: Chat ID to activate
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            all_info = self.get_all_chat_info()
            updated = False
            
            for info in all_info:
                if info.chat_id == chat_id:
                    info.is_active = True
                    updated = True
                    break
            
            if updated:
                self._write_all_chat_info(all_info)
                print(f"Chat ID {chat_id} activated successfully")
                return True
            else:
                print(f"Chat ID {chat_id} not found")
                return False
                
        except Exception as e:
            print(f"Error activating chat ID: {e}")
            return False
    
    def _write_all_chat_info(self, chat_infos: List[ChatInfo]) -> bool:
        """
        Write all chat info to the CSV file (overwrites existing file)
        
        Args:
            chat_infos: List of chat info to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            fieldnames = ['chat_id', 'username', 'first_name', 'last_name', 'date_added', 'is_active']
            
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                for info in chat_infos:
                    writer.writerow(info.to_dict())
            return True
        except Exception as e:
            print(f"Error writing chat info: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored chat IDs
        
        Returns:
            dict: Statistics about chat IDs
        """
        all_info = self.get_all_chat_info()
        active_count = sum(1 for info in all_info if info.is_active)
        inactive_count = len(all_info) - active_count
        
        return {
            'total_chats': len(all_info),
            'active_chats': active_count,
            'inactive_chats': inactive_count,
            'csv_file_path': self.csv_file_path
        }
    
    def clear_all_chat_ids(self) -> bool:
        """
        Clear all chat IDs from the CSV file (keeps headers)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._write_all_chat_info([])
            print("All chat IDs cleared successfully")
            return True
        except Exception as e:
            print(f"Error clearing chat IDs: {e}")
            return False

# Create a singleton instance
storageService = StorageService()
