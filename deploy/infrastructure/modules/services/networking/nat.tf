resource "aws_eip" "nat_gw_eip" {
  vpc = true
}

resource "aws_nat_gateway" "nat_gw" {
  allocation_id = aws_eip.nat_gw_eip.id
  subnet_id     = aws_subnet.subnet_public_az0.id

  tags = merge(
    var.tags,
    {
    }
  )

  depends_on = [aws_internet_gateway.main_igw]
}

resource "aws_route_table" "rt_private_to_nat" {
  vpc_id = aws_vpc.main_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gw.id
  }

  tags = merge(
    var.tags,
    {
    }
  )
}

resource "aws_route_table_association" "rt_private_to_nat_assoc_az0" {
  subnet_id      = aws_subnet.subnet_private_az0.id
  route_table_id = aws_route_table.rt_private_to_nat.id
}

resource "aws_route_table_association" "rt_private_to_nat_assoc_az1" {
  subnet_id      = aws_subnet.subnet_private_az1.id
  route_table_id = aws_route_table.rt_private_to_nat.id
}

resource "aws_route_table" "rt_public_nat_to_igw" {
  vpc_id = aws_vpc.main_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main_igw.id
  }

  tags = merge(
    var.tags,
    {}
  )
}

resource "aws_route_table_association" "rt_public_nat_to_gw_az0" {
  subnet_id      = aws_subnet.subnet_public_az0.id
  route_table_id = aws_route_table.rt_public_nat_to_igw.id
}

resource "aws_route_table_association" "rt_public_nat_to_gw_az1" {
  subnet_id      = aws_subnet.subnet_public_az1.id
  route_table_id = aws_route_table.rt_public_nat_to_igw.id
}