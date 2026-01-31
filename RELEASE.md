# Release Notes

## v0.1.0 – Nina Nashorn

### Supported Use Case

The original core use case is fully implemented:

- Creation of an arbitrary number of tickets per customer
- Marking tickets as paid
- Sending tickets via email
- Admission control using a unique QR code
- Tickets available as individual PNG files (for smartphone display) and as a combined PDF (for printing)
- Customization of ticket appearance and content via configuration files
- Visual and acoustic feedback during ticket validation using a smartphone
- Ability to hide tickets; hidden tickets:
  - are not sent via email
  - are considered invalid during admission control

### Not included / known limitations

The following functionalities are intentionally not part of this release:

- Tickets cannot be seamlessly added to or removed from existing customers
- Tickets cannot be sent multiple times
- There are no overviews for inquiries, offers, or payments

### Technical status

The current implementation is experimental and not intended for production use at this time, primarily due to missing tests for business logic.

- Architecture/implementation: encapsulated API and frontend implementation using Flask, SQLite as metadata storage
- Test coverage: database and utility functions
- API stability: not guaranteed; changes between minor versions are possible (v0.x)
