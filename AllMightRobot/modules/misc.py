from contextlib import suppress

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from aiogram.types import Message
from aiogram.utils.exceptions import BadRequest, MessageNotModified, MessageToDeleteNotFound

from AllMightRobot.decorator import register
from .utils.language import get_strings_dec
from .utils.notes import get_parsed_note_list, send_note, t_unparse_note_item
from .utils.user_details import is_user_admin


@register(cmds='cancel', state='*', allow_kwargs=True)
async def cancel_handle(message, state, **kwargs):
    await state.finish()
    await message.reply('Cancelled.')


async def delmsg_filter_handle(message, chat, data):
    if await is_user_admin(data['chat_id'], message.from_user.id):
        return
    with suppress(MessageToDeleteNotFound):
        await message.delete()


async def replymsg_filter_handler(message, chat, data):
    text, kwargs = await t_unparse_note_item(message, data['reply_text'], chat['chat_id'])
    kwargs['reply_to'] = message.message_id
    with suppress(BadRequest):
        await send_note(chat['chat_id'], text, **kwargs)


@get_strings_dec('misc')
async def replymsg_setup_start(message, strings):
    with suppress(MessageNotModified):
        await message.edit_text(strings['send_text'])


async def replymsg_setup_finish(message, data):
    reply_text = await get_parsed_note_list(message, allow_reply_message=False, split_args=-1)
    return {'reply_text': reply_text}


@get_strings_dec('misc')
async def customise_reason_start(message: Message, strings: dict):
    await message.reply(strings['send_customised_reason'])


@get_strings_dec('misc')
async def customise_reason_finish(message: Message, _: dict, strings: dict):
    if message.text is None:
        await message.reply(strings['expected_text'])
        return False
    elif message.text in {'None'}:
        return {'reason': None}
    return {'reason': message.text}


__filters__ = {
    'delete_message': {
        'title': {'module': 'misc', 'string': 'delmsg_filter_title'},
        'handle': delmsg_filter_handle,
        'del_btn_name': lambda msg, data: f"Del message: {data['handler']}"
    },
    'reply_message': {
        'title': {'module': 'misc', 'string': 'replymsg_filter_title'},
        'handle': replymsg_filter_handler,
        'setup': {
            'start': replymsg_setup_start,
            'finish': replymsg_setup_finish
        },
        'del_btn_name': lambda msg, data: f"Reply to {data['handler']}: \"{data['reply_text'].get('text', 'None')}\" "
    }
}