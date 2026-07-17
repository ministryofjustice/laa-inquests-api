from app.ports.provider_details_port import ProviderDetailsPort
from app.models.application.index import Application, ApplicationProceeding
from app.models.application.certificate import ApplicationCertificate
from app.use_cases.exceptions import ProviderDetailsRetrievalError
from datetime import date


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
        opponent_details = "\n".join(
            body.public_body_description for body in public_bodies
        )

        client_address = (
            application.client.correspondence_address or application.client.home_address
        )

        firm_name = self.provider_details_port.get_firm_name(
            application.provider.firm_code
        )

        if firm_name is None:
            raise ProviderDetailsRetrievalError(
                "Failed to retrieve firm name from provider details service."
            )

        office_address = self.provider_details_port.get_office_address(
            application.provider.office_id
        )

        if office_address is None:
            raise ProviderDetailsRetrievalError(
                "Failed to retrieve office address from provider details service."
            )

        certificate_type = proceeding.certificate_type
        category_of_law = proceeding.category_of_law
        level_of_service = proceeding.level_of_service
        scope_limitation_heading = proceeding.scope_limitation_heading
        scope_limitation_description = proceeding.scope_description
        cost_limitation = str(proceeding.substantive_cost_limitation)
        care_order_description = proceeding.proceeding_description

        effective_date = proceeding.certificate_start_date or date.today()
        date_work_can_commence = proceeding.certificate_start_date or date.today()
        date_current_level_of_service_effective = (
            proceeding.certificate_start_date or date.today()
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
            laa_reference=application.laa_reference,
            date_created=proceeding.certificate_issue_date or date.today(),
            certificate_type=certificate_type,
            category_of_law=category_of_law,
            level_of_service=level_of_service,
            scope_limitation_heading=scope_limitation_heading,
            scope_limitation_description=scope_limitation_description,
            cost_limitation=cost_limitation,
            care_order_description=care_order_description,
            effective_date=effective_date,
            date_work_can_commence=date_work_can_commence,
            date_current_level_of_service_effective=date_current_level_of_service_effective,
            status=status,
            current_proceeding_status=current_proceeding_status,
        )
