# Generate random SQS, SNS, and S3 Resources
# Use localstack conf
import json
import random
from collections import Counter
from string import ascii_lowercase

from asgiref.sync import async_to_sync

from common.config import config
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.aws.session import get_session_for_tenant
from common.lib.tenants import get_all_hosts

# TODO: Generate fake cloudtrail messages for SQS
from common.lib.timeout import Timeout

disable_creation_for_real_aws = True
hosts = get_all_hosts()

SAMPLE = Counter(
    {
        "e": 1202,
        "t": 910,
        "a": 812,
        "o": 768,
        "i": 731,
        "n": 695,
        "s": 628,
        "r": 602,
        "h": 592,
        "d": 432,
        "l": 398,
        "u": 288,
        "c": 271,
        "m": 261,
        "f": 230,
        "y": 211,
        "w": 209,
        "g": 203,
        "p": 182,
        "b": 149,
        "v": 111,
        "k": 69,
        "x": 17,
        "q": 11,
        "j": 10,
        "z": 8,
    }
)

pool = list(SAMPLE.elements())
randpool = []

while len(pool) > 0:
    elem = random.choice(pool)
    randpool.append(elem)
    pool.remove(elem)

LETTERS = set(ascii_lowercase)
VOWELS = set("aeiouy")
CONSONANTS = LETTERS - VOWELS

TAILS = {
    "a": CONSONANTS,
    "b": "bjlr",
    "c": "chjklr",
    "d": "dgjw",
    "e": CONSONANTS,
    "f": "fjlr",
    "g": "ghjlrw",
    "h": "",
    "i": CONSONANTS,
    "j": "",
    "k": "hklrvw",
    "l": "l",
    "m": "cm",
    "n": "gn",
    "o": CONSONANTS,
    "p": "fhlprst",
    "q": "",
    "r": "hrw",
    "s": "chjklmnpqstw",
    "t": "hjrstw",
    "u": CONSONANTS,
    "v": "lv",
    "w": "hr",
    "x": "h",
    "y": "sv",
    "z": "hlvw",
}

# variables expanded:
# w: Word, r: Random Letter, sc: Serial Consonants count, sv: Serial Vowels Count, ss: Serial Same-letter count, lm: Max Length of tails, l: Length of tails


def randomword():
    count = random.randint(1, 4)
    heads = [random.choice(randpool) for i in range(count)]
    i = 0
    segments = []
    while count > 0:
        sc, ss, sv = 0, 0, 0
        w = heads[i]
        if w in CONSONANTS:
            sc += 1
        else:
            sv += 1
        while True:
            r = random.choice(randpool)
            if r in TAILS[w] or r in VOWELS:
                if i == 0 and r == w:
                    continue
                else:
                    if r in VOWELS:
                        sc = 0
                        sv += 1
                        break
                    else:
                        sv = 0
                        sc += 1
                        break
        w += r
        total_chars = 1
        lm = random.randint(2, 5)
        while True:
            if total_chars == lm:
                segments.append(w)
                count -= 1
                break
            f = r
            r = random.choice(randpool)
            if r in TAILS[f] or r in VOWELS:
                if r in VOWELS:
                    sc = 0
                    sv += 1
                elif r in CONSONANTS:
                    sv = 0
                    sc += 1
                if sv == 3 or sc == 3:
                    continue
                if r != f:
                    ss = 0
                if r == f and ss == 1:
                    continue
                if r == f:
                    ss += 1
                w += r
                total_chars += 1
                if random.getrandbits(1):
                    segments.append(w)
                    count -= 1
                    break
        i += 1
    return "".join(segments)


for host in hosts:
    with Timeout(seconds=20):
        accounts_d = async_to_sync(get_account_id_to_name_mapping)(host)
        session = get_session_for_tenant(host)
        authz_tags = [
            {
                "Key": "consoleme-authorized",
                "Value": "ccastrapel@gmail.com:bayareasec@gmail.com",
            },
        ]
        boto_kwargs = config.get_host_specific_key("boto3.client_kwargs", host, {})
        session_kwargs = config.get_host_specific_key("boto3.session_kwargs", host, {})
        if disable_creation_for_real_aws and not boto_kwargs.get("endpoint_url"):
            print(
                f"Refusing to create resources for {host} because there's no custom boto3 endpoint URL"
            )
            continue
        print(f"Creating resources for: {host}.")
        print("Custom Boto3 client kwargs: " + json.dumps(boto_kwargs))
        print("Custom Session kwargs: " + json.dumps(session_kwargs))
        sts = session.client(
            "sts",
            region_name="us-east-1",
            **config.get_host_specific_key("boto3.client_kwargs", host, {}),
        )
        current_role = sts.get_caller_identity()
        account_id = current_role["Account"]
        sqs = session.client(
            "sqs",
            region_name="us-east-1",
            **config.get_host_specific_key("boto3.client_kwargs", host, {}),
        )

        sns = session.client(
            "sns",
            region_name="us-east-1",
            **config.get_host_specific_key("boto3.client_kwargs", host, {}),
        )

        s3 = session.client(
            "s3",
            region_name="us-east-1",
            **config.get_host_specific_key("boto3.client_kwargs", host, {}),
        )

        iam = session.client(
            "iam",
            region_name="us-east-1",
            **config.get_host_specific_key("boto3.client_kwargs", host, {}),
        )

        assume_role_1 = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": [
                            "arn:aws:iam::259868150464:role/ConsoleMeCentralRole",
                            f"arn:aws:iam::{account_id}:role/ConsoleMe1",
                        ]
                    },
                    "Action": "sts:AssumeRole",
                }
            ],
        }

        assume_role_2 = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": f"arn:aws:iam::{account_id}:role/ConsoleMe1"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        try:
            print("Attempting to create role: ConsoleMe1")
            iam.create_role(
                RoleName="ConsoleMe1",
                AssumeRolePolicyDocument=json.dumps(assume_role_1),
                Tags=authz_tags,
            )
            print("Attempting to create role: ConsoleMe2")
            iam.create_role(
                RoleName="ConsoleMe2",
                AssumeRolePolicyDocument=json.dumps(assume_role_2),
                Tags=authz_tags,
            )
        except Exception as e:
            print("Error: " + str(e))

        mp = json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": [
                            "mediastore:Get*",
                            "mediastore:List*",
                            "mediastore:Describe*",
                        ],
                        "Effect": "Allow",
                        "Resource": "*",
                        "Condition": {"Bool": {"aws:SecureTransport": "true"}},
                    }
                ],
            }
        )

        assume_role_ec2 = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                },
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": [
                            "arn:aws:iam::259868150464:role/ConsoleMeCentralRole",
                            # "arn:aws:iam::111111111111:user/moto",
                            # "arn:aws:iam::222222222222:user/moto",
                            # "arn:aws:iam::333333333333:user/moto",
                        ]
                    },
                    "Action": "sts:AssumeRole",
                },
            ],
        }

        for i in range(20):
            try:
                print("Attempting to create managed policy")
                iam.create_policy(
                    PolicyName=randomword(),
                    PolicyDocument=mp,
                )
            except Exception as e:
                print("Error: " + str(e))
            try:
                print("Attempting to create sqs queue")
                sqs.create_queue(
                    QueueName=randomword(),
                )
            except Exception as e:
                print("Error: " + str(e))
            try:
                print("Attempting to create sns topic")
                sns.create_topic(
                    Name=randomword(),
                )
            except Exception as e:
                print("Error: " + str(e))

            try:
                print("Attempting to create s3 bucket")
                s3.create_bucket(
                    Bucket=randomword(),
                )
            except Exception as e:
                print("Error: " + str(e))

            try:
                print("Attempting to create s3 bucket")
                s3.create_bucket(
                    Bucket="noqcache",
                )
            except Exception as e:
                print(f"Unable to create resource: {e}")

            try:
                print("Attempting to create iam role")
                iam.create_role(
                    RoleName=randomword(),
                    AssumeRolePolicyDocument=json.dumps(assume_role_ec2),
                    Tags=authz_tags,
                )
            except Exception as e:
                print("Error: " + str(e))
            try:
                print("Attempting to create iam user")
                iam.create_user(
                    UserName=randomword(),
                    Tags=authz_tags,
                )
            except Exception as e:
                print("Error: " + str(e))
