import tldextract


def email_to_prioritized_subdomains(email):
    """Convert an email address to a list of potential subdomains."""
    extracted = tldextract.extract(email)

    subdomains = []
    if extracted.subdomain:
        subdomains = extracted.subdomain.split(".")

    domains = [extracted.domain] + [f"{d}-{extracted.domain}" for d in subdomains[::-1]]

    # Include the suffix in the last item
    if extracted.suffix:
        suffix = extracted.suffix.replace(".", "-")
        domains.append(f"{domains[-1]}-{suffix}")

    return domains
