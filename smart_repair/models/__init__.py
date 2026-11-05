from .base import utcnow
from .identity import Role, User, UserRole, CustomerProfile, TechnicianProfile, Skill, TechnicianSkill, ServiceCenter
from .catalogue import DeviceCategory, DeviceBrand, DeviceModel, CustomerDevice, SymptomCategory, Symptom, DiagnosticRule, DiagnosticRuleSymptom, DiagnosticResult, Service
from .repairs import RepairRequest, RepairAttachment, Appointment, TechnicianAvailability, TechnicianAssignment, RepairJob, RepairStatusHistory, RepairNote, RepairJobService
from .inventory import Supplier, SparePart, PurchaseOrder, PurchaseOrderItem, InventoryTransaction, PartReservation, RepairPartUsage
from .billing import Estimate, EstimateLine, Invoice, Payment, Review, Notification

MODELS = {m.__tablename__: m for m in [Role, User, UserRole, CustomerProfile, TechnicianProfile,
    Skill, TechnicianSkill, ServiceCenter, DeviceCategory, DeviceBrand, DeviceModel, CustomerDevice,
    SymptomCategory, Symptom, DiagnosticRule, DiagnosticRuleSymptom, DiagnosticResult, RepairRequest,
    RepairAttachment, Appointment, TechnicianAvailability, TechnicianAssignment, RepairJob,
    RepairStatusHistory, RepairNote, Service, RepairJobService, Supplier, SparePart, PurchaseOrder,
    PurchaseOrderItem, InventoryTransaction, PartReservation, RepairPartUsage, Estimate,
    EstimateLine, Invoice, Payment, Review, Notification]}
