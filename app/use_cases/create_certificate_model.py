from app.ports.provider_details_port import ProviderDetailsPort
from app.models.application.index import Address, Application, ApplicationProceeding
from app.models.application.certificate import ApplicationCertificate
from app.use_cases.exceptions import ProviderDetailsRetrievalError
from datetime import date


class CreateCertificateModelUseCase:
    def __init__(self, provider_details_port: ProviderDetailsPort) -> None:
        self.provider_details_port = provider_details_port

    def _format_address(self, address: Address | None) -> str:
        """
        Format an address into a multi-line string.

        Args:
            address: Address object to format, or None

        Returns:
            Formatted address string, or "Not applicable" if address is None
        """
        if not address:
            return "Not applicable"

        parts = [
            address.address_line_1,
            address.address_line_2,
            address.town_or_city,
            address.county,
            address.postcode,
        ]
        return "\n".join(part for part in parts if part)

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
        # Client fields
        # TODO: Just use first name and last name so that we don't have logic to test, template it in the html to combine them
        client_name = f"{application.client.client_first_name} {application.client.client_last_name}"

        # Use correspondence address if available, otherwise fall back to home address
        client_address_obj = (
            application.client.correspondence_address or application.client.home_address
        )
        client_address = self._format_address(client_address_obj)

        # Provider fields
        firm_name = self.provider_details_port.get_firm_name(
            application.provider.firm_code
        )
        if firm_name is None:
            raise ProviderDetailsRetrievalError(
                "Failed to retrieve firm name from provider details service."
            )

        # Office address - hardcoded placeholder for now
        # TODO: Pull this from PDA? Throw errors when some of these defaults aren't available. E.g. if certificate start date doesn't exist we shouldn't be issuing a certificate. We should throw an error and log it.
        office_address = "TBD"

        # Proceeding fields (accessed via ApplicationProceeding properties)
        certificate_type = proceeding.certificate_type
        category_of_law = proceeding.category_of_law
        level_of_service = proceeding.level_of_service
        scope_limitation_heading = proceeding.scope_limitation_heading
        # Map scope_description to scope_limitation_description
        scope_limitation_description = proceeding.scope_description
        cost_limitation = str(proceeding.substantive_cost_limitation)
        care_order_description = proceeding.proceeding_description

        # Application proceeding date fields
        # Use certificate_start_date or fallback to today's date if None
        effective_date = proceeding.certificate_start_date or date.today()
        date_work_can_commence = proceeding.certificate_start_date or date.today()
        date_current_level_of_service_effective = (
            proceeding.certificate_start_date or date.today()
        )

        # Application status fields
        status = application.status
        current_proceeding_status = application.status

        return ApplicationCertificate(
            # Client fields
            client_name=client_name,
            client_address=client_address,
            # Provider fields
            firm_name=firm_name,
            office_address=office_address,
            # Proceeding fields
            certificate_type=certificate_type,
            category_of_law=category_of_law,
            level_of_service=level_of_service,
            scope_limitation_heading=scope_limitation_heading,
            scope_limitation_description=scope_limitation_description,
            cost_limitation=cost_limitation,
            care_order_description=care_order_description,
            # Application proceeding date fields
            effective_date=effective_date,
            date_work_can_commence=date_work_can_commence,
            date_current_level_of_service_effective=date_current_level_of_service_effective,
            # Application status fields
            status=status,
            current_proceeding_status=current_proceeding_status,
        )
