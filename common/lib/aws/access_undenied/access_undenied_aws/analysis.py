import json
from typing import Any, Dict, Optional, TextIO, Union

from aws_error_utils import ClientError, errors

from common.config import config
from common.lib.aws.access_undenied.access_undenied_aws import (
    common,
    event,
    event_permission_data,
    iam_policy_data,
    result_details,
    results,
    simulate_custom_policy_context_generator,
    simulate_custom_policy_helper,
)
from common.lib.aws.access_undenied.access_undenied_aws.results import AnalysisResult

logger = config.get_logger(__name__)


def _write_to_file(output_file: TextIO, output_json: Dict[str, Any]) -> None:
    if output_file is not None and output_file:
        output_file.write(json.dumps(output_json, indent=2))
        output_file.close()


def _handle_encoded_message(
    config: common.Config, error_message: str
) -> Optional[Dict[str, Any]]:
    # Handle the case of EC2 encoded message, decode the message and output the result
    # https://docs.aws.amazon.com/STS/latest/APIReference/API_DecodeAuthorizationMessage.html
    logger.debug("Encoded EC2 Authorization error message present, attempt to decode")
    return json.loads(
        config.session.client("sts").decode_authorization_message(
            EncodedMessage=error_message.split(
                "Encoded authorization failure message: "
            )[-1]
        )["DecodedMessage"]
    )


def _is_valid_encoded_message(error_message) -> bool:
    if error_message and "Encoded authorization failure message" in error_message:
        if error_message[-3:] == "...":
            logger.error(
                "Could not decode authorization message because the message"
                " in the CloudTrail event is incomplete. CloudTrail does"
                " not store error messages longer than 1024 chars."
                " Attempting regular analysis."
            )
            return False
        return True


def _write_to_output_buffer(
    config: common.Config,
    result: Union[Dict[str, Any], results.Result],
) -> None:
    """
    Output result to file, stdout, or both - as per the configuration.
    """
    if not config.suppress_output:
        logger.debug(str(result))
    if config.output_file:
        config.output_json.get("Results", []).append(json.loads(str(result)))


def analyze(
    config: common.Config, raw_event: Dict[str, Any]
) -> Optional[results.Result]:
    if raw_event.get("errorCode") not in [
        "AccessDenied",
        "Client.UnauthorizedOperation",
    ]:
        logger.debug(
            "Event without AccessDenied/Client.UnauthorizedOperation"
            " error code not handled:"
            f" [eventID:{raw_event['eventID']}, "
            f"errorCode:{raw_event.get('errorCode')}]"
        )
        return None

    event_ = event.Event(raw_event)
    logger.info(f"AccessDenied cloudtrail_event found: [eventID={event_.event_id}]")
    logger.debug(f"[errorMessage:{event_.error_message}]")

    if _is_valid_encoded_message(event_.error_message):
        try:
            return _handle_encoded_message(config, event_.error_message)
        except (errors.InvalidAuthorizationMessageException,) as access_undenied_error:
            logger.debug(
                "Could not decode authorization message:"
                f" {access_undenied_error}. Continuing"
                " analysis as usual."
            )

    try:
        logger.debug(
            "Analyzing event permission data (event Principal, Action,"
            " Resources, and Conditions)..."
        )
        event_permission_data_ = event_permission_data.EventPermissionData.from_event(
            event_, config
        )
        if event_permission_data_.is_missing_allow_in_identity_based_policy:
            logger.debug(
                "Quick-exit condition: simple missing allow in identity-based"
                " policy with all parameters known."
            )
            return _create_simple_missing_allow_analysis_result(
                cloudtrail_event_=event_,
                event_permission_data_=event_permission_data_,
            )

        logger.debug("Gathering all relevant IAM policies for permission analysis...")
        iam_policy_data_ = iam_policy_data.IamPolicyData.from_event_permission_data(
            config=config,
            event_permission_data_=event_permission_data_,
            region=event_.region,
        )

        logger.debug("Generating context values for condition assessment...")
        context = simulate_custom_policy_context_generator.SimulateCustomPolicyContextGenerator(
            config=config,
            event_permission_data_=event_permission_data_,
            cloudtrail_event_=event_,
        ).generate_context(
            simulate_custom_policy_helper.generate_context_key_list_for_simulate_custom_policy(
                iam_policy_data_, config.iam_client
            )
        )

        logger.debug(
            "Calling iam:SimulateCustomPolicy with the relevant arguments"
            " and analyzing the responses..."
        )
        simulate_custom_policy_request = (
            simulate_custom_policy_helper.generate_simulate_custom_policy_request(
                iam_policy_data_=iam_policy_data_,
                event_permission_data_=event_permission_data_,
                context=context,
            )
        )
        analysis_result = simulate_custom_policy_helper.simulate_custom_policies(
            config,
            event_,
            event_permission_data_,
            iam_policy_data_,
            simulate_custom_policy_request,
        )
        if analysis_result:
            return analysis_result
    except common.AccessUndeniedError as access_undenied_error:
        # logger.error(
        #     str(access_undenied_error)
        #     + f" [eventID:{raw_event.get('eventID', '<None>')}]"
        # )
        return results.ErrorResult(
            event_id=raw_event.get("eventID", "<None>"),
            assessment_result=access_undenied_error.access_denied_reason,
            error_message=str(access_undenied_error),
        )

    except (ClientError) as access_undenied_error:
        logger.error(
            repr(access_undenied_error)
            + f" [eventID:{raw_event.get('eventID', '<None>')}]"
        )
        return results.ErrorResult(
            event_id=raw_event.get("eventID", "<None>"),
            assessment_result=common.AccessDeniedReason.ERROR,
            error_message=str(access_undenied_error),
        )


def analyze_cloudtrail_events(config: common.Config, raw_events_file_path):
    raw_events = json.load(raw_events_file_path)
    # Multiple CloudTrail log records in file or single event
    for raw_event in raw_events.get("Records") or [raw_events]:
        result = analyze(config, raw_event)
        if result:
            _write_to_output_buffer(config, result)
    _write_to_file(config.output_file, config.output_json)


def _create_simple_missing_allow_analysis_result(
    cloudtrail_event_: event.Event,
    event_permission_data_: event_permission_data.EventPermissionData,
) -> AnalysisResult:
    return AnalysisResult(
        event_id=cloudtrail_event_.event_id,
        assessment_result=common.AccessDeniedReason.IDENTITY_POLICY_MISSING_ALLOW,
        result_details_=result_details.MissingAllowResultDetails(
            simulate_custom_policy_response={
                "EvalActionName": event_permission_data_.iam_permission,
                "EvalResourceName": event_permission_data_.resource.arn,
                "EvalDecision": "implicitDeny",
                "MatchedStatements": [],
                "MissingContextValues": [],
            },
            missing_allow_reason=common.AccessDeniedReason.IDENTITY_POLICY_MISSING_ALLOW,
            target_resource_arn=event_permission_data_.resource.arn,
            target_principal_arn=event_permission_data_.principal.arn,
        ),
    )
