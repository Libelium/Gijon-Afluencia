from config.rabbitmq import RabbitConfig
import pika
import ssl


class RabbitClient:
    def __init__(self, conf: RabbitConfig) -> None:

        # SSL Context for TLS configuration of Amazon MQ for RabbitMQ
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.set_ciphers('ECDHE+AESGCM:!ECDSA')
        if conf.security == "amqps" and conf.ca_file_path:
            context.load_verify_locations(conf.ca_file_path)  # Path to your CA certificate
        parameters = pika.URLParameters(conf.connection_slug)
        parameters.ssl_options = pika.SSLOptions(context=context)
        
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
