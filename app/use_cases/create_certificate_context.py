from datetime import UTC, datetime

from app.models.application.certificate import ApplicationCertificate
from app.models.application.index import Application, ApplicationProceeding
from app.ports.provider_details_port import ProviderDetailsPort


class CreateCertificateContextUseCase:
    def __init__(self, provider_details_port: ProviderDetailsPort) -> None:
        self.provider_details_port = provider_details_port

    def populate_certificate_context(
        self, application: Application, proceeding: ApplicationProceeding
    ) -> ApplicationCertificate:
        """
        Populate certificate context from application and proceeding data.

        Args:
            application: Application object with all relationships loaded
            proceeding: ApplicationProceeding object with proceeding relationship loaded

        Returns:
            ApplicationCertificate with all fields populated from application data
        """

        client_name = f"{application.client.client_first_name} {application.client.client_last_name}"

        public_bodies = application.public_bodies
        opponent_details = (
            [body.public_body_description for body in public_bodies]
            if public_bodies
            else None
        )

        firm_name = self.provider_details_port.get_firm_name(
            application.provider.firm_code
        )

        office_address = self.provider_details_port.get_office_address(
            application.provider.office_id
        )

        if application.client.correspondence_address_source == "USE_PROVIDER_ADDRESS":
            client_address = office_address.model_copy()
        elif (
            application.client.correspondence_address_source == "USE_SPECIFIED_ADDRESS"
        ):
            client_address = application.client.correspondence_address
        else:
            client_address = application.client.home_address

        if application.client.correspondence_recipient:
            client_address.address_line_1 = f"c/o {application.client.correspondence_recipient.recipient_name} {client_address.address_line_1}"

        certificate_type = proceeding.certificate_type
        category_of_law = proceeding.category_of_law
        level_of_service = proceeding.level_of_service
        scope_limitation_heading = proceeding.scope_limitation_heading
        scope_limitation_description = proceeding.scope_description
        cost_limitation = proceeding.substantive_cost_limitation
        proceeding_name = proceeding.proceeding_name
        proceeding_description = proceeding.proceeding_description

        effective_date = (
            proceeding.certificate_start_date or datetime.now(tz=UTC).date()
        )
        date_work_can_commence = (
            proceeding.certificate_start_date or datetime.now(tz=UTC).date()
        )
        date_current_level_of_service_effective = (
            proceeding.certificate_start_date or datetime.now(tz=UTC).date()
        )

        # Application status fields
        status = application.status
        current_proceeding_status = (
            application.status in ["CLOSED", "WITHDRAWN"] and "CLOSED" or "LIVE"
        )

        return ApplicationCertificate(
            client_name=client_name,
            client_address=client_address,
            opponent_details=opponent_details,
            firm_name=firm_name,
            office_address=office_address,
            laa_reference=str(application.laa_reference),
            date_created=proceeding.certificate_issue_date
            or datetime.now(tz=UTC).date(),
            certificate_type=certificate_type,
            category_of_law=category_of_law,
            level_of_service=level_of_service,
            scope_limitation_heading=scope_limitation_heading,
            scope_limitation_description=scope_limitation_description,
            cost_limitation=cost_limitation,
            cost_limitation_effective_date=proceeding.substantive_cost_limitation_effective_date,
            proceeding_name=proceeding_name,
            proceeding_description=proceeding_description,
            effective_date=effective_date,
            end_date=proceeding.certificate_end_date,
            date_work_can_commence=date_work_can_commence,
            date_current_level_of_service_effective=date_current_level_of_service_effective,
            status=status,
            current_proceeding_status=current_proceeding_status,
        )

    def prepare_context_for_display(
        self, context: ApplicationCertificate
    ) -> ApplicationCertificate:
        """Prepare the certificate context for display by formatting enum fields."""
        context.certificate_type = context.certificate_type.capitalize()
        context.status = context.status.capitalize()
        context.category_of_law = context.category_of_law.capitalize()
        context.current_proceeding_status = (
            context.current_proceeding_status.capitalize()
        )
        context.level_of_service = context.level_of_service.replace(
            "_", " "
        ).capitalize()
        context.scope_limitation_heading = context.scope_limitation_heading.replace(
            "_", " "
        ).capitalize()
        return context
