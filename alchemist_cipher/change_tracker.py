# change_tracker.py

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Dict, Optional, Union
from datetime import datetime

class ImplementationStatus(Enum):
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    TESTED = auto()

class PriorityLevel(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()

@dataclass
class ChangeItem:
    id: str
    title: str
    description: str
    status: ImplementationStatus
    priority: PriorityLevel
    file_path: str
    created_date: datetime
    modified_date: datetime
    completed_date: Optional[datetime] = None
    dependencies: List[str] = None
    tests: List[str] = None
    notes: str = ""

class ChangeTracker:
    """Tracks implementation changes across the Alchemist's Cipher project."""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.changes: Dict[str, ChangeItem] = {}
        self.version = "0.1.0"
        self.components = {
            "verification": {
                "social_deduction": ImplementationStatus.NOT_STARTED,
                "relationship_map": ImplementationStatus.NOT_STARTED,
                "agent_simulation": ImplementationStatus.NOT_STARTED,
                "ordering": ImplementationStatus.NOT_STARTED,
                "scheduling": ImplementationStatus.NOT_STARTED,
                "dilemma": ImplementationStatus.NOT_STARTED,
                "logic_grid": ImplementationStatus.COMPLETED,  # Already implemented
                "common_sense_gap": ImplementationStatus.NOT_STARTED
            },
            "generation": {
                "ordering_puzzle": ImplementationStatus.IN_PROGRESS,
                "scheduling_puzzle": ImplementationStatus.IN_PROGRESS,
                "dilemma_puzzle": ImplementationStatus.IN_PROGRESS,
                "social_deduction_puzzle": ImplementationStatus.COMPLETED,
                "relationship_map_puzzle": ImplementationStatus.COMPLETED,
                "agent_simulation_puzzle": ImplementationStatus.COMPLETED,
                "logic_grid_puzzle": ImplementationStatus.COMPLETED,
            },
            "variety": {
                "name_pools": ImplementationStatus.IN_PROGRESS,
                "trait_pools": ImplementationStatus.IN_PROGRESS,
                "scenario_templates": ImplementationStatus.NOT_STARTED,
                "difficulty_progression": ImplementationStatus.NOT_STARTED
            },
            "ai_solver": {
                "openai_integration": ImplementationStatus.NOT_STARTED,
                "reasoning_visualization": ImplementationStatus.NOT_STARTED
            }
        }
    
    def add_change(self, change: ChangeItem) -> str:
        """Adds a new change item to track."""
        self.changes[change.id] = change
        return change.id
    
    def update_change(self, change_id: str, updates: Dict) -> bool:
        """Updates an existing change item."""
        if change_id not in self.changes:
            return False
        
        change = self.changes[change_id]
        for key, value in updates.items():
            if hasattr(change, key):
                setattr(change, key, value)
        
        change.modified_date = datetime.now()
        if updates.get('status') == ImplementationStatus.COMPLETED:
            change.completed_date = datetime.now()
        
        return True
    
    def update_component_status(self, component: str, subcomponent: str, status: ImplementationStatus) -> bool:
        """Updates the status of a component/subcomponent."""
        if component not in self.components or subcomponent not in self.components[component]:
            return False
        
        self.components[component][subcomponent] = status
        return True
    
    def get_component_status(self, component: str, subcomponent: str = None) -> Union[ImplementationStatus, Dict[str, ImplementationStatus]]:
        """Gets the status of a component or all its subcomponents."""
        if component not in self.components:
            raise ValueError(f"Component '{component}' not found")
        
        if subcomponent:
            if subcomponent not in self.components[component]:
                raise ValueError(f"Subcomponent '{subcomponent}' not found in '{component}'")
            return self.components[component][subcomponent]
        else:
            return self.components[component]
    
    def get_priority_matrix(self) -> Dict[PriorityLevel, List[ChangeItem]]:
        """Creates a priority matrix of remaining tasks."""
        matrix = {level: [] for level in PriorityLevel}
        
        for change in self.changes.values():
            if change.status != ImplementationStatus.COMPLETED and change.status != ImplementationStatus.TESTED:
                matrix[change.priority].append(change)
        
        return matrix
    
    def get_progress_report(self) -> Dict:
        """Generates a progress report across all components."""
        report = {
            "version": self.version,
            "total_changes": len(self.changes),
            "completed_changes": sum(1 for c in self.changes.values() if c.status in 
                                    [ImplementationStatus.COMPLETED, ImplementationStatus.TESTED]),
            "component_progress": {}
        }
        
        for component, subcomponents in self.components.items():
            total = len(subcomponents)
            completed = sum(1 for status in subcomponents.values() if status == ImplementationStatus.COMPLETED)
            testing = sum(1 for status in subcomponents.values() if status == ImplementationStatus.TESTED)
            
            report["component_progress"][component] = {
                "total": total,
                "completed": completed,
                "testing": testing,
                "completion_percentage": (completed + testing) / total * 100 if total > 0 else 0
            }
        
        return report
    
    def export_report(self, format_type: str = "text") -> str:
        """Exports the change tracking report in the specified format."""
        report = self.get_progress_report()
        
        if format_type == "text":
            return self._format_text_report(report)
        elif format_type == "markdown":
            return self._format_markdown_report(report)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
    
    def _format_text_report(self, report: Dict) -> str:
        """Formats the report as plain text."""
        lines = [
            f"Alchemist's Cipher Project - Version {report['version']}",
            f"Progress Report: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"Total Changes: {report['total_changes']}",
            f"Completed Changes: {report['completed_changes']} ({report['completed_changes']/report['total_changes']*100:.1f}% complete)",
            "",
            "Component Progress:"
        ]
        
        for component, stats in report["component_progress"].items():
            lines.append(f"  {component.capitalize()}: {stats['completion_percentage']:.1f}% complete")
            lines.append(f"    {stats['completed']} completed + {stats['testing']} testing out of {stats['total']} total")
        
        return "\n".join(lines)
    
    def _format_markdown_report(self, report: Dict) -> str:
        """Formats the report as markdown."""
        lines = [
            f"# Alchemist's Cipher Project - Version {report['version']}",
            f"## Progress Report: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"**Total Changes:** {report['total_changes']}  ",
            f"**Completed Changes:** {report['completed_changes']} ({report['completed_changes']/report['total_changes']*100:.1f}% complete)",
            "",
            "## Component Progress"
        ]
        
        for component, stats in report["component_progress"].items():
            lines.append(f"### {component.capitalize()}: {stats['completion_percentage']:.1f}% complete")
            lines.append(f"- {stats['completed']} completed + {stats['testing']} testing out of {stats['total']} total")
        
        return "\n".join(lines)