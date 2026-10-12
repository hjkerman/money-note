// Explicit opt-in adapter only; normal API client does not import E2.
import '../api_client.dart';
import 'transport.dart';

AuthenticatedSegmentedTransport segmentedTransportForApi(
        MoneyNoteApiClient api) =>
    api.withIsolatedTransport((client, origin, credential) =>
        AuthenticatedSegmentedTransport(
            client: client, origin: origin, credential: credential));
