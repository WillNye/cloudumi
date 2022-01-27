resource "aws_vpc" "main_vpc" {
  cidr_block       = "10.${var.attributes}.0.0/16"
  enable_dns_support = true
  enable_dns_hostnames = true
  instance_tenancy = "default"

  tags = merge(
    var.tags,
    {
    }
  )
}

resource "aws_internet_gateway" "main_igw" {
  vpc_id = aws_vpc.main_vpc.id

  tags = merge(
    var.tags,
    {
    }
  )
}

resource "aws_subnet" "subnet_public_az0" {
  vpc_id = aws_vpc.main_vpc.id
  cidr_block = "10.${var.attributes}.254.0/24"
  map_public_ip_on_launch = "true"
  availability_zone = element(var.subnet_azs, 0)
  tags = merge(
    var.tags,
    {
    }
  )

  timeouts {
    create = var.timeout
  }
}

resource "aws_subnet" "subnet_public_az1" {
  vpc_id = aws_vpc.main_vpc.id
  cidr_block = "10.${var.attributes}.255.0/24"
  map_public_ip_on_launch = "true"
  availability_zone = element(var.subnet_azs, 1)
  tags = merge(
    var.tags,
    {
    }
  )

  timeouts {
    create = var.timeout
  }
}


resource "aws_subnet" "subnet_private_az0" {
  vpc_id = aws_vpc.main_vpc.id
  cidr_block = "10.${var.attributes}.0.0/18"
  availability_zone = element(var.subnet_azs, 0)
  tags = merge(
    var.tags,
    {
    }
  )

  timeouts {
    create = var.timeout
  }
}

resource "aws_subnet" "subnet_private_az1" {
  vpc_id = aws_vpc.main_vpc.id
  cidr_block = "10.${var.attributes}.64.0/18"
  availability_zone = element(var.subnet_azs, 1)
  tags = merge(
    var.tags,
    {
    }
  )

  timeouts {
    create = var.timeout
  }
}
