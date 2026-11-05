CREATE TABLE device_brands (
	name VARCHAR(80) NOT NULL,
	website VARCHAR(255),
	is_active BOOLEAN NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_device_brands PRIMARY KEY (id),
	CONSTRAINT uq_device_brands_name UNIQUE (name)
)

;


CREATE TABLE device_categories (
	name VARCHAR(80) NOT NULL,
	description TEXT,
	is_active BOOLEAN NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_device_categories PRIMARY KEY (id),
	CONSTRAINT uq_device_categories_name UNIQUE (name)
)

;


CREATE TABLE roles (
	name VARCHAR(40) NOT NULL,
	description TEXT,
	is_system BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_roles PRIMARY KEY (id),
	CONSTRAINT uq_roles_name UNIQUE (name)
)

;


CREATE TABLE service_centers (
	name VARCHAR(100) NOT NULL,
	address TEXT NOT NULL,
	city VARCHAR(80) NOT NULL,
	phone VARCHAR(25),
	opening_time TIME NOT NULL,
	closing_time TIME NOT NULL,
	is_active BOOLEAN NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_service_centers PRIMARY KEY (id),
	CONSTRAINT ck_service_centers_hours_order CHECK (closing_time > opening_time)
)

;


CREATE TABLE skills (
	name VARCHAR(100) NOT NULL,
	description TEXT,
	is_active BOOLEAN NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_skills PRIMARY KEY (id),
	CONSTRAINT uq_skills_name UNIQUE (name)
)

;


CREATE TABLE suppliers (
	name VARCHAR(120) NOT NULL,
	contact_name VARCHAR(100),
	phone VARCHAR(25),
	email VARCHAR(254),
	address TEXT,
	is_active BOOLEAN NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_suppliers PRIMARY KEY (id)
)

;


CREATE TABLE symptom_categories (
	name VARCHAR(80) NOT NULL,
	description TEXT,
	is_active BOOLEAN NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_symptom_categories PRIMARY KEY (id),
	CONSTRAINT uq_symptom_categories_name UNIQUE (name)
)

;


CREATE TABLE users (
	full_name VARCHAR(100) NOT NULL,
	email VARCHAR(254) NOT NULL,
	phone VARCHAR(25),
	password_hash VARCHAR(256) NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_users PRIMARY KEY (id),
	CONSTRAINT uq_users_phone UNIQUE (phone)
)

;


CREATE TABLE customer_profiles (
	user_id INTEGER NOT NULL,
	address TEXT,
	city VARCHAR(80),
	preferred_contact VARCHAR(20) NOT NULL,
	created_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_customer_profiles PRIMARY KEY (id),
	CONSTRAINT fk_customer_profiles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
)

;


CREATE TABLE device_models (
	brand_id INTEGER NOT NULL,
	category_id INTEGER NOT NULL,
	model_name VARCHAR(100) NOT NULL,
	release_year INTEGER,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_device_models PRIMARY KEY (id),
	CONSTRAINT uq_device_models_brand_id UNIQUE (brand_id, model_name),
	CONSTRAINT fk_device_models_brand_id_device_brands FOREIGN KEY(brand_id) REFERENCES device_brands (id) ON DELETE RESTRICT,
	CONSTRAINT fk_device_models_category_id_device_categories FOREIGN KEY(category_id) REFERENCES device_categories (id) ON DELETE RESTRICT
)

;


CREATE TABLE diagnostic_rules (
	title VARCHAR(150) NOT NULL,
	category_id INTEGER,
	probable_fault VARCHAR(200) NOT NULL,
	explanation TEXT NOT NULL,
	suggested_action TEXT NOT NULL,
	severity VARCHAR(20) NOT NULL,
	estimated_minutes INTEGER NOT NULL,
	confidence_score NUMERIC(5, 2) NOT NULL,
	priority INTEGER NOT NULL,
	is_active BOOLEAN NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_diagnostic_rules PRIMARY KEY (id),
	CONSTRAINT fk_diagnostic_rules_category_id_device_categories FOREIGN KEY(category_id) REFERENCES device_categories (id) ON DELETE RESTRICT
)

;


CREATE TABLE notifications (
	user_id INTEGER NOT NULL,
	title VARCHAR(150) NOT NULL,
	message TEXT NOT NULL,
	channel VARCHAR(20) NOT NULL,
	is_read BOOLEAN NOT NULL,
	related_type VARCHAR(40),
	related_id INTEGER,
	created_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_notifications PRIMARY KEY (id),
	CONSTRAINT fk_notifications_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
)

;


CREATE TABLE purchase_orders (
	supplier_id INTEGER NOT NULL,
	created_by_user_id INTEGER NOT NULL,
	order_number VARCHAR(40) NOT NULL,
	order_date DATE NOT NULL,
	expected_date DATE,
	status VARCHAR(25) NOT NULL,
	total_amount NUMERIC(10, 2) NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_purchase_orders PRIMARY KEY (id),
	CONSTRAINT fk_purchase_orders_supplier_id_suppliers FOREIGN KEY(supplier_id) REFERENCES suppliers (id) ON DELETE RESTRICT,
	CONSTRAINT fk_purchase_orders_created_by_user_id_users FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE RESTRICT,
	CONSTRAINT uq_purchase_orders_order_number UNIQUE (order_number)
)

;


CREATE TABLE services (
	name VARCHAR(120) NOT NULL,
	description TEXT,
	base_price NUMERIC(10, 2) NOT NULL,
	estimated_minutes INTEGER NOT NULL,
	is_active BOOLEAN NOT NULL,
	required_skill_id INTEGER,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_services PRIMARY KEY (id),
	CONSTRAINT ck_services_price_nonnegative CHECK (base_price >= 0),
	CONSTRAINT uq_services_name UNIQUE (name),
	CONSTRAINT fk_services_required_skill_id_skills FOREIGN KEY(required_skill_id) REFERENCES skills (id) ON DELETE RESTRICT
)

;


CREATE TABLE spare_parts (
	sku VARCHAR(50) NOT NULL,
	name VARCHAR(120) NOT NULL,
	description TEXT,
	compatible_category_id INTEGER,
	unit_cost NUMERIC(10, 2) NOT NULL,
	sale_price NUMERIC(10, 2) NOT NULL,
	quantity_on_hand INTEGER NOT NULL,
	reorder_level INTEGER NOT NULL,
	is_active BOOLEAN NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_spare_parts PRIMARY KEY (id),
	CONSTRAINT ck_spare_parts_stock_nonnegative CHECK (quantity_on_hand >= 0 AND reorder_level >= 0 AND unit_cost >= 0 AND sale_price >= 0),
	CONSTRAINT uq_spare_parts_sku UNIQUE (sku),
	CONSTRAINT fk_spare_parts_compatible_category_id_device_categories FOREIGN KEY(compatible_category_id) REFERENCES device_categories (id) ON DELETE RESTRICT
)

;


CREATE TABLE symptoms (
	category_id INTEGER NOT NULL,
	name VARCHAR(120) NOT NULL,
	description TEXT,
	default_severity VARCHAR(20) NOT NULL,
	is_active BOOLEAN NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_symptoms PRIMARY KEY (id),
	CONSTRAINT fk_symptoms_category_id_symptom_categories FOREIGN KEY(category_id) REFERENCES symptom_categories (id) ON DELETE RESTRICT
)

;


CREATE TABLE technician_profiles (
	user_id INTEGER NOT NULL,
	service_center_id INTEGER NOT NULL,
	employee_code VARCHAR(40) NOT NULL,
	experience_years INTEGER NOT NULL,
	bio TEXT,
	is_available BOOLEAN NOT NULL,
	hire_date DATE,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_technician_profiles PRIMARY KEY (id),
	CONSTRAINT ck_technician_profiles_experience_nonnegative CHECK (experience_years >= 0),
	CONSTRAINT fk_technician_profiles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT,
	CONSTRAINT fk_technician_profiles_service_center_id_service_centers FOREIGN KEY(service_center_id) REFERENCES service_centers (id) ON DELETE RESTRICT,
	CONSTRAINT uq_technician_profiles_employee_code UNIQUE (employee_code)
)

;


CREATE TABLE user_roles (
	user_id INTEGER NOT NULL,
	role_id INTEGER NOT NULL,
	assigned_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_user_roles PRIMARY KEY (id),
	CONSTRAINT uq_user_roles_user_id UNIQUE (user_id, role_id),
	CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT,
	CONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE RESTRICT
)

;


CREATE TABLE customer_devices (
	customer_id INTEGER NOT NULL,
	device_model_id INTEGER NOT NULL,
	serial_number VARCHAR(100),
	purchase_date DATE,
	nickname VARCHAR(100) NOT NULL,
	notes TEXT,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_customer_devices PRIMARY KEY (id),
	CONSTRAINT fk_customer_devices_customer_id_customer_profiles FOREIGN KEY(customer_id) REFERENCES customer_profiles (id) ON DELETE RESTRICT,
	CONSTRAINT fk_customer_devices_device_model_id_device_models FOREIGN KEY(device_model_id) REFERENCES device_models (id) ON DELETE RESTRICT
)

;


CREATE TABLE diagnostic_rule_symptoms (
	rule_id INTEGER NOT NULL,
	symptom_id INTEGER NOT NULL,
	weight INTEGER NOT NULL,
	is_required BOOLEAN NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_diagnostic_rule_symptoms PRIMARY KEY (id),
	CONSTRAINT uq_diagnostic_rule_symptoms_rule_id UNIQUE (rule_id, symptom_id),
	CONSTRAINT ck_diagnostic_rule_symptoms_positive_weight CHECK (weight > 0),
	CONSTRAINT fk_diagnostic_rule_symptoms_rule_id_diagnostic_rules FOREIGN KEY(rule_id) REFERENCES diagnostic_rules (id) ON DELETE RESTRICT,
	CONSTRAINT fk_diagnostic_rule_symptoms_symptom_id_symptoms FOREIGN KEY(symptom_id) REFERENCES symptoms (id) ON DELETE RESTRICT
)

;


CREATE TABLE inventory_transactions (
	spare_part_id INTEGER NOT NULL,
	performed_by_user_id INTEGER NOT NULL,
	transaction_type VARCHAR(30) NOT NULL,
	quantity_change INTEGER NOT NULL,
	reference_type VARCHAR(40),
	reference_id INTEGER,
	notes TEXT,
	created_at DATETIME NOT NULL,
	reversed_at DATETIME,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_inventory_transactions PRIMARY KEY (id),
	CONSTRAINT fk_inventory_transactions_spare_part_id_spare_parts FOREIGN KEY(spare_part_id) REFERENCES spare_parts (id) ON DELETE RESTRICT,
	CONSTRAINT fk_inventory_transactions_performed_by_user_id_users FOREIGN KEY(performed_by_user_id) REFERENCES users (id) ON DELETE RESTRICT
)

;


CREATE TABLE purchase_order_items (
	purchase_order_id INTEGER NOT NULL,
	spare_part_id INTEGER NOT NULL,
	quantity_ordered INTEGER NOT NULL,
	unit_cost NUMERIC(10, 2) NOT NULL,
	quantity_received INTEGER NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_purchase_order_items PRIMARY KEY (id),
	CONSTRAINT ck_purchase_order_items_receipt_range CHECK (quantity_ordered > 0 AND quantity_received >= 0 AND quantity_received <= quantity_ordered AND unit_cost >= 0),
	CONSTRAINT fk_purchase_order_items_purchase_order_id_purchase_orders FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders (id) ON DELETE RESTRICT,
	CONSTRAINT fk_purchase_order_items_spare_part_id_spare_parts FOREIGN KEY(spare_part_id) REFERENCES spare_parts (id) ON DELETE RESTRICT
)

;


CREATE TABLE technician_availability (
	technician_id INTEGER NOT NULL,
	available_date DATE NOT NULL,
	start_time TIME NOT NULL,
	end_time TIME NOT NULL,
	is_available BOOLEAN NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_technician_availability PRIMARY KEY (id),
	CONSTRAINT uq_technician_availability_technician_id UNIQUE (technician_id, available_date, start_time, end_time),
	CONSTRAINT ck_technician_availability_availability_order CHECK (end_time > start_time),
	CONSTRAINT fk_technician_availability_technician_id_technician_profiles FOREIGN KEY(technician_id) REFERENCES technician_profiles (id) ON DELETE RESTRICT
)

;


CREATE TABLE technician_skills (
	technician_id INTEGER NOT NULL,
	skill_id INTEGER NOT NULL,
	proficiency_level INTEGER NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_technician_skills PRIMARY KEY (id),
	CONSTRAINT uq_technician_skills_technician_id UNIQUE (technician_id, skill_id),
	CONSTRAINT ck_technician_skills_proficiency_range CHECK (proficiency_level BETWEEN 1 AND 5),
	CONSTRAINT fk_technician_skills_technician_id_technician_profiles FOREIGN KEY(technician_id) REFERENCES technician_profiles (id) ON DELETE RESTRICT,
	CONSTRAINT fk_technician_skills_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
)

;


CREATE TABLE repair_requests (
	customer_id INTEGER NOT NULL,
	customer_device_id INTEGER NOT NULL,
	service_center_id INTEGER,
	required_skill_id INTEGER,
	request_code VARCHAR(40) NOT NULL,
	issue_description TEXT NOT NULL,
	selected_symptoms TEXT NOT NULL,
	preferred_date DATE,
	urgency VARCHAR(20) NOT NULL,
	status VARCHAR(40) NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_repair_requests PRIMARY KEY (id),
	CONSTRAINT fk_repair_requests_customer_id_customer_profiles FOREIGN KEY(customer_id) REFERENCES customer_profiles (id) ON DELETE RESTRICT,
	CONSTRAINT fk_repair_requests_customer_device_id_customer_devices FOREIGN KEY(customer_device_id) REFERENCES customer_devices (id) ON DELETE RESTRICT,
	CONSTRAINT fk_repair_requests_service_center_id_service_centers FOREIGN KEY(service_center_id) REFERENCES service_centers (id) ON DELETE RESTRICT,
	CONSTRAINT fk_repair_requests_required_skill_id_skills FOREIGN KEY(required_skill_id) REFERENCES skills (id) ON DELETE RESTRICT
)

;


CREATE TABLE appointments (
	repair_request_id INTEGER NOT NULL,
	service_center_id INTEGER NOT NULL,
	scheduled_start DATETIME NOT NULL,
	scheduled_end DATETIME NOT NULL,
	status VARCHAR(25) NOT NULL,
	created_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_appointments PRIMARY KEY (id),
	CONSTRAINT ck_appointments_appointment_order CHECK (scheduled_end > scheduled_start),
	CONSTRAINT fk_appointments_repair_request_id_repair_requests FOREIGN KEY(repair_request_id) REFERENCES repair_requests (id) ON DELETE RESTRICT,
	CONSTRAINT fk_appointments_service_center_id_service_centers FOREIGN KEY(service_center_id) REFERENCES service_centers (id) ON DELETE RESTRICT
)

;


CREATE TABLE diagnostic_results (
	repair_request_id INTEGER NOT NULL,
	rule_id INTEGER,
	result_summary TEXT NOT NULL,
	confidence_score NUMERIC(5, 2) NOT NULL,
	suggested_action TEXT NOT NULL,
	created_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_diagnostic_results PRIMARY KEY (id),
	CONSTRAINT fk_diagnostic_results_repair_request_id_repair_requests FOREIGN KEY(repair_request_id) REFERENCES repair_requests (id) ON DELETE RESTRICT,
	CONSTRAINT fk_diagnostic_results_rule_id_diagnostic_rules FOREIGN KEY(rule_id) REFERENCES diagnostic_rules (id) ON DELETE RESTRICT
)

;


CREATE TABLE repair_attachments (
	repair_request_id INTEGER NOT NULL,
	uploaded_by_user_id INTEGER NOT NULL,
	file_name VARCHAR(255) NOT NULL,
	file_path VARCHAR(255) NOT NULL,
	mime_type VARCHAR(100) NOT NULL,
	file_size INTEGER NOT NULL,
	uploaded_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_repair_attachments PRIMARY KEY (id),
	CONSTRAINT fk_repair_attachments_repair_request_id_repair_requests FOREIGN KEY(repair_request_id) REFERENCES repair_requests (id) ON DELETE RESTRICT,
	CONSTRAINT fk_repair_attachments_uploaded_by_user_id_users FOREIGN KEY(uploaded_by_user_id) REFERENCES users (id) ON DELETE RESTRICT,
	CONSTRAINT uq_repair_attachments_file_path UNIQUE (file_path)
)

;


CREATE TABLE technician_assignments (
	repair_request_id INTEGER NOT NULL,
	technician_id INTEGER NOT NULL,
	assigned_by_user_id INTEGER NOT NULL,
	assigned_at DATETIME NOT NULL,
	status VARCHAR(30) NOT NULL,
	notes TEXT,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_technician_assignments PRIMARY KEY (id),
	CONSTRAINT fk_technician_assignments_repair_request_id_repair_requests FOREIGN KEY(repair_request_id) REFERENCES repair_requests (id) ON DELETE RESTRICT,
	CONSTRAINT fk_technician_assignments_technician_id_technician_profiles FOREIGN KEY(technician_id) REFERENCES technician_profiles (id) ON DELETE RESTRICT,
	CONSTRAINT fk_technician_assignments_assigned_by_user_id_users FOREIGN KEY(assigned_by_user_id) REFERENCES users (id) ON DELETE RESTRICT
)

;


CREATE TABLE repair_jobs (
	repair_request_id INTEGER NOT NULL,
	service_center_id INTEGER NOT NULL,
	job_code VARCHAR(40) NOT NULL,
	assigned_assignment_id INTEGER,
	started_at DATETIME,
	completed_at DATETIME,
	status VARCHAR(40) NOT NULL,
	warranty_days INTEGER NOT NULL,
	internal_cost NUMERIC(10, 2) NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_repair_jobs PRIMARY KEY (id),
	CONSTRAINT fk_repair_jobs_repair_request_id_repair_requests FOREIGN KEY(repair_request_id) REFERENCES repair_requests (id) ON DELETE RESTRICT,
	CONSTRAINT fk_repair_jobs_service_center_id_service_centers FOREIGN KEY(service_center_id) REFERENCES service_centers (id) ON DELETE RESTRICT,
	CONSTRAINT uq_repair_jobs_job_code UNIQUE (job_code),
	CONSTRAINT fk_repair_jobs_assigned_assignment_id_technician_assignments FOREIGN KEY(assigned_assignment_id) REFERENCES technician_assignments (id) ON DELETE RESTRICT
)

;


CREATE TABLE estimates (
	repair_job_id INTEGER NOT NULL,
	prepared_by_user_id INTEGER NOT NULL,
	estimate_number VARCHAR(40) NOT NULL,
	labor_total NUMERIC(10, 2) NOT NULL,
	parts_total NUMERIC(10, 2) NOT NULL,
	tax_amount NUMERIC(10, 2) NOT NULL,
	discount_amount NUMERIC(10, 2) NOT NULL,
	grand_total NUMERIC(10, 2) NOT NULL,
	status VARCHAR(25) NOT NULL,
	valid_until DATE NOT NULL,
	decided_at DATETIME,
	created_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_estimates PRIMARY KEY (id),
	CONSTRAINT ck_estimates_estimate_nonnegative CHECK (labor_total >= 0 AND parts_total >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND grand_total >= 0),
	CONSTRAINT fk_estimates_repair_job_id_repair_jobs FOREIGN KEY(repair_job_id) REFERENCES repair_jobs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_estimates_prepared_by_user_id_users FOREIGN KEY(prepared_by_user_id) REFERENCES users (id) ON DELETE RESTRICT,
	CONSTRAINT uq_estimates_estimate_number UNIQUE (estimate_number)
)

;


CREATE TABLE part_reservations (
	repair_job_id INTEGER NOT NULL,
	spare_part_id INTEGER NOT NULL,
	reserved_quantity INTEGER NOT NULL,
	status VARCHAR(25) NOT NULL,
	reserved_at DATETIME NOT NULL,
	released_at DATETIME,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_part_reservations PRIMARY KEY (id),
	CONSTRAINT ck_part_reservations_reservation_positive CHECK (reserved_quantity > 0),
	CONSTRAINT fk_part_reservations_repair_job_id_repair_jobs FOREIGN KEY(repair_job_id) REFERENCES repair_jobs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_part_reservations_spare_part_id_spare_parts FOREIGN KEY(spare_part_id) REFERENCES spare_parts (id) ON DELETE RESTRICT
)

;


CREATE TABLE repair_job_services (
	repair_job_id INTEGER NOT NULL,
	service_id INTEGER NOT NULL,
	quantity INTEGER NOT NULL,
	agreed_unit_price NUMERIC(10, 2) NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_repair_job_services PRIMARY KEY (id),
	CONSTRAINT uq_repair_job_services_repair_job_id UNIQUE (repair_job_id, service_id),
	CONSTRAINT ck_repair_job_services_valid_service_amount CHECK (quantity > 0 AND agreed_unit_price >= 0),
	CONSTRAINT fk_repair_job_services_repair_job_id_repair_jobs FOREIGN KEY(repair_job_id) REFERENCES repair_jobs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_repair_job_services_service_id_services FOREIGN KEY(service_id) REFERENCES services (id) ON DELETE RESTRICT
)

;


CREATE TABLE repair_notes (
	repair_job_id INTEGER NOT NULL,
	author_user_id INTEGER NOT NULL,
	note_text TEXT NOT NULL,
	is_customer_visible BOOLEAN NOT NULL,
	created_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_repair_notes PRIMARY KEY (id),
	CONSTRAINT fk_repair_notes_repair_job_id_repair_jobs FOREIGN KEY(repair_job_id) REFERENCES repair_jobs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_repair_notes_author_user_id_users FOREIGN KEY(author_user_id) REFERENCES users (id) ON DELETE RESTRICT
)

;


CREATE TABLE repair_status_history (
	repair_job_id INTEGER NOT NULL,
	changed_by_user_id INTEGER NOT NULL,
	old_status VARCHAR(40) NOT NULL,
	new_status VARCHAR(40) NOT NULL,
	note TEXT,
	changed_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_repair_status_history PRIMARY KEY (id),
	CONSTRAINT fk_repair_status_history_repair_job_id_repair_jobs FOREIGN KEY(repair_job_id) REFERENCES repair_jobs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_repair_status_history_changed_by_user_id_users FOREIGN KEY(changed_by_user_id) REFERENCES users (id) ON DELETE RESTRICT
)

;


CREATE TABLE reviews (
	repair_job_id INTEGER NOT NULL,
	customer_id INTEGER NOT NULL,
	rating INTEGER NOT NULL,
	comment TEXT,
	created_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_reviews PRIMARY KEY (id),
	CONSTRAINT uq_reviews_repair_job_id UNIQUE (repair_job_id, customer_id),
	CONSTRAINT ck_reviews_rating_range CHECK (rating BETWEEN 1 AND 5),
	CONSTRAINT fk_reviews_repair_job_id_repair_jobs FOREIGN KEY(repair_job_id) REFERENCES repair_jobs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_reviews_customer_id_customer_profiles FOREIGN KEY(customer_id) REFERENCES customer_profiles (id) ON DELETE RESTRICT
)

;


CREATE TABLE estimate_lines (
	estimate_id INTEGER NOT NULL,
	service_id INTEGER,
	spare_part_id INTEGER,
	description VARCHAR(200) NOT NULL,
	quantity INTEGER NOT NULL,
	unit_price NUMERIC(10, 2) NOT NULL,
	line_total NUMERIC(10, 2) NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_estimate_lines PRIMARY KEY (id),
	CONSTRAINT ck_estimate_lines_one_line_source CHECK ((service_id IS NULL) != (spare_part_id IS NULL)),
	CONSTRAINT ck_estimate_lines_line_positive CHECK (quantity > 0 AND unit_price >= 0 AND line_total >= 0),
	CONSTRAINT fk_estimate_lines_estimate_id_estimates FOREIGN KEY(estimate_id) REFERENCES estimates (id) ON DELETE RESTRICT,
	CONSTRAINT fk_estimate_lines_service_id_services FOREIGN KEY(service_id) REFERENCES services (id) ON DELETE RESTRICT,
	CONSTRAINT fk_estimate_lines_spare_part_id_spare_parts FOREIGN KEY(spare_part_id) REFERENCES spare_parts (id) ON DELETE RESTRICT
)

;


CREATE TABLE invoices (
	repair_job_id INTEGER NOT NULL,
	estimate_id INTEGER,
	invoice_number VARCHAR(40) NOT NULL,
	issued_at DATETIME NOT NULL,
	due_date DATE,
	subtotal NUMERIC(10, 2) NOT NULL,
	tax_amount NUMERIC(10, 2) NOT NULL,
	discount_amount NUMERIC(10, 2) NOT NULL,
	total_amount NUMERIC(10, 2) NOT NULL,
	status VARCHAR(25) NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_invoices PRIMARY KEY (id),
	CONSTRAINT ck_invoices_invoice_nonnegative CHECK (subtotal >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND total_amount >= 0),
	CONSTRAINT fk_invoices_repair_job_id_repair_jobs FOREIGN KEY(repair_job_id) REFERENCES repair_jobs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_invoices_estimate_id_estimates FOREIGN KEY(estimate_id) REFERENCES estimates (id) ON DELETE RESTRICT,
	CONSTRAINT uq_invoices_invoice_number UNIQUE (invoice_number)
)

;


CREATE TABLE repair_part_usages (
	repair_job_id INTEGER NOT NULL,
	spare_part_id INTEGER NOT NULL,
	technician_id INTEGER NOT NULL,
	reservation_id INTEGER,
	quantity_used INTEGER NOT NULL,
	unit_cost_at_use NUMERIC(10, 2) NOT NULL,
	used_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_repair_part_usages PRIMARY KEY (id),
	CONSTRAINT ck_repair_part_usages_usage_positive CHECK (quantity_used > 0 AND unit_cost_at_use >= 0),
	CONSTRAINT fk_repair_part_usages_repair_job_id_repair_jobs FOREIGN KEY(repair_job_id) REFERENCES repair_jobs (id) ON DELETE RESTRICT,
	CONSTRAINT fk_repair_part_usages_spare_part_id_spare_parts FOREIGN KEY(spare_part_id) REFERENCES spare_parts (id) ON DELETE RESTRICT,
	CONSTRAINT fk_repair_part_usages_technician_id_technician_profiles FOREIGN KEY(technician_id) REFERENCES technician_profiles (id) ON DELETE RESTRICT,
	CONSTRAINT fk_repair_part_usages_reservation_id_part_reservations FOREIGN KEY(reservation_id) REFERENCES part_reservations (id) ON DELETE RESTRICT
)

;


CREATE TABLE payments (
	invoice_id INTEGER NOT NULL,
	received_by_user_id INTEGER,
	payment_reference VARCHAR(80),
	amount NUMERIC(10, 2) NOT NULL,
	method VARCHAR(25) NOT NULL,
	status VARCHAR(25) NOT NULL,
	paid_at DATETIME,
	created_at DATETIME NOT NULL,
	id INTEGER NOT NULL,
	archived_at DATETIME,
	archive_reason TEXT,
	audit_log TEXT NOT NULL,
	CONSTRAINT pk_payments PRIMARY KEY (id),
	CONSTRAINT ck_payments_payment_positive CHECK (amount > 0),
	CONSTRAINT fk_payments_invoice_id_invoices FOREIGN KEY(invoice_id) REFERENCES invoices (id) ON DELETE RESTRICT,
	CONSTRAINT fk_payments_received_by_user_id_users FOREIGN KEY(received_by_user_id) REFERENCES users (id) ON DELETE RESTRICT,
	CONSTRAINT uq_payments_payment_reference UNIQUE (payment_reference)
)

;
