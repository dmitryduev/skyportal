from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Instrument, Telescope
from ...enum_types import ALLOWED_BANDPASSES


class InstrumentHandler(BaseHandler):
    @permissions(['System admin'])
    def post(self):
        # See bottom of this file for redoc docstring -- moved it there so that
        # it could be made an f-string.

        data = self.get_json()
        telescope_id = data.get('telescope_id')
        telescope = Telescope.query.get(telescope_id)
        if not telescope:
            return self.error('Invalid telescope ID.')

        schema = Instrument.__schema__()
        try:
            instrument = schema.load(data)
        except ValidationError as exc:
            return self.error(
                'Invalid/missing parameters: ' f'{exc.normalized_messages()}'
            )
        instrument.telescope = telescope
        DBSession().add(instrument)
        DBSession().commit()

        return self.success(data={"id": instrument.id})

    @auth_or_token
    def get(self, instrument_id=None):
        """
        ---
        single:
          description: Retrieve an instrument
          tags:
            - instruments
          parameters:
            - in: path
              name: instrument_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleInstrument
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all instruments
          tags:
            - instruments
          parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Filter by name (exact match)
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfInstruments
            400:
              content:
                application/json:
                  schema: Error
        """
        if instrument_id is not None:
            instrument = Instrument.query.get(int(instrument_id))

            if instrument is None:
                return self.error(
                    f"Could not load instrument {instrument_id}",
                    data={"instrument_id": instrument_id},
                )
            return self.success(data=instrument)

        inst_name = self.get_query_argument("name", None)
        query = Instrument.query
        if inst_name is not None:
            query = query.filter(Instrument.name == inst_name)
        return self.success(data=query.all())

    @permissions(['System admin'])
    def put(self, instrument_id):
        """
        ---
        description: Update instrument
        tags:
          - instruments
        parameters:
          - in: path
            name: instrument_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: InstrumentNoID
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        data['id'] = int(instrument_id)

        schema = Instrument.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as exc:
            return self.error(
                'Invalid/missing parameters: ' f'{exc.normalized_messages()}'
            )
        DBSession().commit()

        return self.success()

    @permissions(['System admin'])
    def delete(self, instrument_id):
        """
        ---
        description: Delete an instrument
        tags:
          - instruments
        parameters:
          - in: path
            name: instrument_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        DBSession().query(Instrument).filter(
            Instrument.id == int(instrument_id)
        ).delete()
        DBSession().commit()

        return self.success()


InstrumentHandler.post.__doc__ = f"""
        ---
        description: Add a new instrument
        tags:
          - instruments
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                - $ref: "#/components/schemas/InstrumentNoID"
                - type: object
                  properties:
                    filters:
                      type: array
                      items:
                        type: string
                        enum: {list(ALLOWED_BANDPASSES)}
                      description: >-
                        List of filters on the instrument. If the instrument
                        has no filters (e.g., because it is a spectrograph),
                        leave blank or pass the empty list.
                      default: []
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            id:
                              type: integer
                              description: New instrument ID
          400:
            content:
              application/json:
                schema: Error
        """
