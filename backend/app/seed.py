"""Carga datos de demostración (empresas, diagnósticos e interacciones).

Uso:  python -m app.seed
"""
from __future__ import annotations

import random

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app, init_db
from app.models import Company, PipelineStage, User, UserRole
from app.security import hash_password
from app.services.questionnaire import QUESTIONS

COMPANIES = [
    ("Panadería La Espiga", "manufactura", 18, "Puerto Boyacá"),
    ("Ferretería El Tornillo", "comercio", 15, "Puerto Boyacá"),
    ("Moda Andina SAS", "comercio", 35, "Puerto Boyacá"),
    ("Consultores Contables JM", "servicios", 6, "Puerto Boyacá"),
    ("Clínica Dental Sonríe", "servicios", 22, "Puerto Boyacá"),
    ("Agencia de Viajes Rumbo", "servicios", 12, "Puerto Boyacá"),
    ("Confecciones Valle", "manufactura", 60, "Puerto Boyacá"),
    ("Muebles Roble Fino", "manufactura", 28, "Puerto Boyacá"),
    ("Alimentos del Campo", "manufactura", 120, "Puerto Boyacá"),
    ("Café Origen Huila", "comercio", 4, "Puerto Boyacá"),
]


def ensure_advisors(db) -> None:
    # 1. José Cristóbal Rosero
    adv1 = db.scalar(select(User).where(User.email == "asesor@impulsodigital.co"))
    if not adv1:
        db.add(User(
            email="asesor@impulsodigital.co",
            full_name="José Cristóbal Rosero",
            role=UserRole.COMERCIAL,
            hashed_password=hash_password("Asesor123*"),
        ))
    else:
        adv1.full_name = "José Cristóbal Rosero"
        adv1.role = UserRole.COMERCIAL

    # 2. Edinson Reynel Castillo
    adv2 = db.scalar(select(User).where(User.email == "edinson.castillo@impulsodigital.co"))
    if not adv2:
        db.add(User(
            email="edinson.castillo@impulsodigital.co",
            full_name="Edinson Reynel Castillo",
            role=UserRole.COMERCIAL,
            hashed_password=hash_password("Asesor123*"),
        ))
    else:
        adv2.full_name = "Edinson Reynel Castillo"
        adv2.role = UserRole.COMERCIAL

    db.commit()


def main() -> None:
    random.seed(42)
    init_db()
    with SessionLocal() as db:
        ensure_advisors(db)
        if db.scalar(select(Company).limit(1)):
            print("La base de datos ya tiene empresas; verificando Módulo 3...")
            seed_module_3(db)

            print("Datos de demostración actualizados.")
            return


        for i, (name, sector, employees, city) in enumerate(COMPANIES):
            bias = random.random()
            answers = {
                q.code: q.options[min(3, max(0, int(random.gauss(bias * 3, 0.8))))].value
                for q in QUESTIONS
            }
            r = client.post("/api/public/diagnostics", json={
                "company": {"name": name, "nit": f"90000{i:04d}", "sector": sector,
                            "employees": employees, "city": city},
                "contact": {"full_name": f"Contacto {name.split()[0]}",
                            "email": f"contacto{i}@example.com", "phone": f"300{i:07d}"},
                "answers": answers,
                "data_consent": True,
                "marketing_consent": bool(i % 2),
            })
            r.raise_for_status()
            print(f"  ✔ {name}: {r.json()['total_score']} → {r.json()['recommended_package']['name']}")

        with SessionLocal() as db:
            stages = [PipelineStage.GANADO, PipelineStage.GANADO, PipelineStage.PROPUESTA,
                      PipelineStage.CONTACTADO, PipelineStage.PERDIDO]
            for company, stage in zip(db.scalars(select(Company).order_by(Company.id)), stages):
                company.stage = stage
                if stage == PipelineStage.GANADO:
                    d = company.diagnostics[-1]
                    d.converted, d.purchased_package = True, d.recommended_package
            db.commit()

            # Módulo 2 Demo: Crear proyectos, entregables, usuario cliente y materiales de capacitación
            from app.models import Deliverable, DeliverableStatus, Project, ProjectStatus, SupportTicket, TicketMessage, TicketPriority, TicketStatus, TrainingMaterial

            # 1. Usuario cliente para la primera empresa (Panadería La Espiga)
            comp_1 = db.scalar(select(Company).order_by(Company.id).limit(1))
            if comp_1 and not db.scalar(select(User).where(User.email == "cliente@laespiga.com")):
                client_user = User(
                    email="cliente@laespiga.com",
                    full_name="Don Efraín - Panadería La Espiga",
                    role=UserRole.CLIENTE,
                    company_id=comp_1.id,
                    hashed_password=hash_password("Cliente123*"),
                )
                db.add(client_user)
                db.flush()

                # Proyecto en fase de desarrollo (Staging)
                project = Project(
                    company_id=comp_1.id,
                    title="Sitio Web E-commerce y Pedidos por WhatsApp",
                    package=comp_1.diagnostics[-1].recommended_package,
                    status=ProjectStatus.STAGING,
                    progress_percent=85,
                    staging_url="https://laespiga.staging.impulsodigital.co",
                    production_url="https://laespiga.co",
                )
                db.add(project)
                db.flush()

                # Entregables con estados y feedback
                db.add_all([
                    Deliverable(
                        project_id=project.id,
                        title="1. Wireframes y Diseño UI (Figma)",
                        description="Diseño visual de las pantallas principales incluyendo catálogo y carrito de compras.",
                        preview_url="https://figma.com/file/demo",
                        status=DeliverableStatus.APROBADO,
                        client_feedback="Aprobado. Los colores reflejan muy bien la identidad de la panadería.",
                    ),
                    Deliverable(
                        project_id=project.id,
                        title="2. Desarrollo Frontend e Integración WhatsApp",
                        description="Maquetación del sitio en React y botón flotante para enviar pedido preformateado a WhatsApp.",
                        preview_url="https://laespiga.staging.impulsodigital.co",
                        status=DeliverableStatus.APROBADO,
                        client_feedback="El botón de WhatsApp funciona perfecto desde el celular.",
                    ),
                    Deliverable(
                        project_id=project.id,
                        title="3. Configuración de Hosting y Dominio",
                        description="Despliegue en servidores, certificado SSL y configuración del dominio laespiga.co.",
                        preview_url="https://laespiga.staging.impulsodigital.co",
                        status=DeliverableStatus.REVISION,
                        client_feedback="Aún veo un error de seguridad al entrar desde algunos navegadores. Por favor revisar el SSL.",
                    ),
                ])

                # Ticket de soporte inicial
                ticket = SupportTicket(
                    company_id=comp_1.id,
                    created_by_id=client_user.id,
                    subject="Problema al actualizar el catálogo de tortas",
                    description="Intenté subir nuevas fotos para la temporada de madres, pero la página se queda cargando.",
                    priority=TicketPriority.MEDIA,
                    status=TicketStatus.EN_PROCESO,
                )
                db.add(ticket)
                db.flush()

                admin_u = db.scalar(select(User).where(User.role == UserRole.ADMIN))
                db.add_all([
                    TicketMessage(ticket_id=ticket.id, user_id=client_user.id, message=ticket.description),
                    TicketMessage(
                        ticket_id=ticket.id,
                        user_id=admin_u.id,
                        message="Hola Don Guillermo. En la sección de Capacitación subimos el video tutorial de WhatsApp Business donde explicamos paso a paso cómo definir mensajes de ausencia y horarios comerciales.",
                    ),
                ])

            # Materiales de capacitación en video y manuales
            if not db.scalar(select(TrainingMaterial).limit(1)):
                db.add_all([
                    TrainingMaterial(
                        title="1. Dominando WhatsApp Business para Pymes",
                        description="Configuración de perfil de empresa, catálogo de productos, respuestas rápidas y etiquetas de clientes.",
                        category="WhatsApp Business",
                        package_required=None,
                        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        manual_url="https://impulsodigital.co/manuales/whatsapp-business-guia.pdf",
                        duration_minutes=18,
                        order_index=1,
                    ),
                    TrainingMaterial(
                        title="2. Cómo Gestionar su Catálogo y Productos",
                        description="Aprenda a subir nuevos productos, actualizar precios, fotos y controlar disponibilidad.",
                        category="Presencia Web",
                        package_required=None,
                        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        manual_url="https://impulsodigital.co/manuales/gestion-catalogo.pdf",
                        duration_minutes=12,
                        order_index=2,
                    ),
                    TrainingMaterial(
                        title="3. Configuración de Pasarela de Pagos (PSE y Tarjetas)",
                        description="Guía completa para recibir pagos electrónicos, verificar transacciones y retiros a cuenta bancaria.",
                        category="E-commerce y Pagos",
                        package_required=Package.INTEGRAL,
                        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        manual_url="https://impulsodigital.co/manuales/pasarela-pagos-pse.pdf",
                        duration_minutes=25,
                        order_index=3,
                    ),
                    TrainingMaterial(
                        title="4. Publicidad Digital Básica en Meta Ads",
                        description="Estrategias de inversión local en Puerto Boyacá para atraer clientes desde Instagram y Facebook.",
                        category="Marketing Digital",
                        package_required=Package.INTEGRAL,
                        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        manual_url="https://impulsodigital.co/manuales/meta-ads-local.pdf",
                        duration_minutes=30,
                        order_index=4,
                    ),
                ])

            seed_module_3(db)
            db.commit()
    print("Datos de demostración cargados.")


def seed_module_3(db) -> None:
    from datetime import timedelta
    from app.models import (
        FreelancerProfile,
        FreelancerSpeciality,
        FreelancerTask,
        Milestone,
        MilestonePaymentStatus,
        MilestoneStage,
        Project,
        SLAStatus,
        TaskStatus,
        TicketPriority,
        UserRole,
        utcnow,
    )

    freelancer_user = db.scalar(select(User).where(User.email == "freelancer@impulsodigital.co"))
    if not freelancer_user:
        freelancer_user = User(
            email="freelancer@impulsodigital.co",
            full_name="Carlos Desarrollador Freelance",
            role=UserRole.FREELANCER,
            hashed_password=hash_password("Freelance123*"),
        )
        db.add(freelancer_user)
        db.flush()

        profile = FreelancerProfile(
            user_id=freelancer_user.id,
            speciality=FreelancerSpeciality.DESARROLLO_WEB,
            skills=["React", "TypeScript", "FastAPI", "TailwindCSS", "PostgreSQL"],
            hourly_rate=55000.0,
            bank_info="Bancolombia Ahorros #312-998877-12",
            rating=4.9,
            completed_tasks_count=12,
            on_time_delivery_rate=0.96,  # 96% de cumplimiento (meta operativa >=95%)
            is_available=True,
        )
        db.add(profile)
        db.flush()

    # Vincular hitos y tareas al primer proyecto
    project_1 = db.scalar(select(Project).order_by(Project.id).limit(1))
    if project_1 and not db.scalar(select(Milestone).where(Milestone.project_id == project_1.id).limit(1)):
        m1 = Milestone(
            project_id=project_1.id,
            title="Hito 1: Inicio y Levantamiento de Requerimientos",
            stage=MilestoneStage.INICIO,
            payout_amount=600000.0,
            payment_status=MilestonePaymentStatus.LIBERADO,
            requires_client_approval=True,
            client_approved=True,
            qa_approved=True,
            released_at=utcnow() - timedelta(days=7),
            notes="Aprobado en kickoff con Panadería La Espiga.",
        )
        m2 = Milestone(
            project_id=project_1.id,
            title="Hito 2: Aprobación de Arquitectura y Diseño UI Staging",
            stage=MilestoneStage.APROBACION_DISENO,
            payout_amount=1200000.0,
            payment_status=MilestonePaymentStatus.PENDIENTE_APROBACION,
            requires_client_approval=True,
            client_approved=True,
            qa_approved=True,
            notes="QA verificado al 96%. Pendiente de liberación por tesorería.",
        )
        m3 = Milestone(
            project_id=project_1.id,
            title="Hito 3: Entrega Final y Puesta en Marcha en Producción",
            stage=MilestoneStage.ENTREGA_FINAL,
            payout_amount=1800000.0,
            payment_status=MilestonePaymentStatus.BLOQUEADO,
            requires_client_approval=True,
            client_approved=False,
            qa_approved=False,
            notes="Bloqueado hasta finalización de auditoría de seguridad y visto bueno final.",
        )
        db.add_all([m1, m2, m3])
        db.flush()

        now = utcnow()
        t1 = FreelancerTask(
            project_id=project_1.id,
            milestone_id=m1.id,
            assigned_freelancer_id=freelancer_user.id,
            title="Diseño UI/UX (Figma)",
            description="Creación de wireframes y diseño de alta fidelidad para el e-commerce de La Espiga.",
            deliverable_url="https://figma.com/file/demo",
            status=TaskStatus.COMPLETADA,
            priority=TicketPriority.ALTA,
            sla_hours_allotted=48,
            due_date=now - timedelta(days=8),
            submitted_at=now - timedelta(days=9),
            completed_at=now - timedelta(days=8, hours=2),
            sla_status=SLAStatus.A_TIEMPO,
            qa_score=96,
            qa_feedback="Excelente adaptabilidad móvil. Los colores coinciden con el manual de marca.",
            qa_checklist={"responsive": True, "performance": True, "security": True},
        )
        t2 = FreelancerTask(
            project_id=project_1.id,
            milestone_id=m2.id,
            assigned_freelancer_id=freelancer_user.id,
            title="Certificado SSL y Dominio",
            description="Configuración de Let's Encrypt y DNS para laespiga.co.",
            deliverable_url="https://laespiga.co",
            status=TaskStatus.COMPLETADA,
            priority=TicketPriority.ALTA,
            sla_hours_allotted=24,
            due_date=now - timedelta(days=3),
            submitted_at=now - timedelta(days=3, hours=4),
            completed_at=now - timedelta(days=3, hours=1),
            sla_status=SLAStatus.A_TIEMPO,
            qa_score=98,
            qa_feedback="SSL Let's Encrypt configurado con calificación A+ en SSL Labs.",
            qa_checklist={"ssl_valid": True, "no_mixed_content": True, "uptime": True},
        )
        t3 = FreelancerTask(
            project_id=project_1.id,
            milestone_id=m3.id,
            assigned_freelancer_id=freelancer_user.id,
            title="Integración de Analítica Web y SEO Local Puerto Boyacá",
            description="Configuración de Google Search Console, metaetiquetas de geolocalización y Open Graph.",
            deliverable_url="https://laespiga.staging.impulsodigital.co/seo-audit",
            status=TaskStatus.EN_QA,
            priority=TicketPriority.MEDIA,
            sla_hours_allotted=48,
            due_date=now + timedelta(days=2),
            submitted_at=now - timedelta(hours=3),
            sla_status=SLAStatus.A_TIEMPO,
            qa_score=None,
            qa_feedback=None,
            qa_checklist={},
        )
        t4 = FreelancerTask(
            project_id=project_1.id,
            milestone_id=m3.id,
            assigned_freelancer_id=freelancer_user.id,
            title="Pruebas de Carga y Seguridad contra Vulnerabilidades OWASP",
            description="Simulación de tráfico concurrente y validación de políticas CORS y headers de seguridad.",
            status=TaskStatus.EN_PROCESO,
            priority=TicketPriority.ALTA,
            sla_hours_allotted=72,
            due_date=now + timedelta(days=4),
            sla_status=SLAStatus.A_TIEMPO,
        )
        db.add_all([t1, t2, t3, t4])
    db.commit()



if __name__ == "__main__":
    main()
